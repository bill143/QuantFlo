"""Validation battery: in-sample, out-of-sample, walk-forward, Monte Carlo + overfit guard.

The battery produces REAL numbers and a pass/reject verdict. The overfitting guard
REJECTS a strategy that performs only in-sample: a configuration optimized on the
in-sample window must also clear the held-out out-of-sample window, walk-forward
folds, and a Monte Carlo robustness band, or it is rejected with a recorded reason.
No trading logic beyond signal evaluation — nothing is executed anywhere.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import pandas as pd

from quantflo.backtest.engine import BacktestConfig, Backtester, BacktestResult
from quantflo.backtest.metrics import PerformanceMetrics, sharpe_ratio
from quantflo.strategies.base import Strategy


@dataclass(frozen=True)
class ValidationConfig:
    """Thresholds for the validation battery + overfit guard."""

    oos_fraction: float = 0.3
    walk_forward_folds: int = 4
    monte_carlo_runs: int = 300
    monte_carlo_seed: int = 42
    min_oos_sharpe: float = 0.3
    min_oos_trades: int = 5
    min_walk_forward_positive_fraction: float = 0.5
    min_mc_prob_positive: float = 0.5
    overfit_oos_is_ratio: float = 0.4  # OOS Sharpe must be >= this x IS Sharpe


@dataclass(frozen=True)
class MonteCarloSummary:
    runs: int
    sharpe_p05: float
    sharpe_p50: float
    sharpe_p95: float
    prob_positive_return: float


@dataclass(frozen=True)
class FoldResult:
    fold: int
    params: dict[str, Any]
    metrics: PerformanceMetrics


@dataclass(frozen=True)
class ValidationReport:
    strategy_key: str
    instrument: str
    best_params: dict[str, Any]
    in_sample: PerformanceMetrics
    out_of_sample: PerformanceMetrics
    walk_forward: list[FoldResult]
    monte_carlo: MonteCarloSummary
    passed: bool
    reason: str


def _run(strategy: Strategy, bars: pd.DataFrame, bt: BacktestConfig) -> BacktestResult:
    frame = bars.reset_index(drop=True)
    return Backtester(bt).run(frame, strategy.generate_signals(frame).reset_index(drop=True))


def recalibrate(
    strategy_cls: type[Strategy],
    bars: pd.DataFrame,
    param_grid: list[dict[str, Any]],
    bt: BacktestConfig,
    min_trades: int,
) -> tuple[dict[str, Any], PerformanceMetrics]:
    """Grid-search params maximizing in-sample Sharpe (penalizing too-few-trades)."""
    best_params = param_grid[0]
    best_metrics: PerformanceMetrics | None = None
    best_score = float("-inf")
    for params in param_grid:
        metrics = _run(strategy_cls(params), bars, bt).metrics
        score = metrics.sharpe if metrics.trade_count >= min_trades else metrics.sharpe - 100.0
        if score > best_score:
            best_score, best_params, best_metrics = score, params, metrics
    assert best_metrics is not None
    return best_params, best_metrics


def walk_forward(
    strategy_cls: type[Strategy],
    bars: pd.DataFrame,
    param_grid: list[dict[str, Any]],
    bt: BacktestConfig,
    folds: int,
    min_trades: int,
) -> list[FoldResult]:
    """Expanding-window walk-forward: re-optimize on prior data, test on the next fold."""
    n = len(bars)
    fold_size = n // (folds + 1)
    results: list[FoldResult] = []
    if fold_size < 20:
        return results
    for k in range(1, folds + 1):
        train = bars.iloc[: k * fold_size]
        test = bars.iloc[k * fold_size : (k + 1) * fold_size]
        if len(test) < 20:
            continue
        params, _ = recalibrate(strategy_cls, train, param_grid, bt, min_trades)
        metrics = _run(strategy_cls(params), test, bt).metrics
        results.append(FoldResult(fold=k, params=params, metrics=metrics))
    return results


def monte_carlo(
    returns: pd.Series, runs: int, periods_per_year: float, seed: int
) -> MonteCarloSummary:
    """Bootstrap-resample the bar returns to build a robustness distribution."""
    values = [float(x) for x in pd.to_numeric(returns, errors="coerce").dropna().to_numpy()]
    if len(values) < 2:
        return MonteCarloSummary(runs, 0.0, 0.0, 0.0, 0.0)
    rng = random.Random(seed)
    sharpes: list[float] = []
    total_returns: list[float] = []
    for _ in range(runs):
        sample = pd.Series(rng.choices(values, k=len(values)))
        sharpes.append(sharpe_ratio(sample, periods_per_year))
        total_returns.append(float((1.0 + sample).prod() - 1.0))
    sharpes.sort()

    def pct(sorted_vals: list[float], p: float) -> float:
        return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]

    return MonteCarloSummary(
        runs=runs,
        sharpe_p05=round(pct(sharpes, 0.05), 6),
        sharpe_p50=round(pct(sharpes, 0.50), 6),
        sharpe_p95=round(pct(sharpes, 0.95), 6),
        prob_positive_return=round(sum(1 for t in total_returns if t > 0) / len(total_returns), 6),
    )


def _judge(
    in_sample: PerformanceMetrics,
    out_of_sample: PerformanceMetrics,
    wf: list[FoldResult],
    mc: MonteCarloSummary,
    cfg: ValidationConfig,
) -> tuple[bool, str]:
    if out_of_sample.trade_count < cfg.min_oos_trades:
        return False, f"insufficient OOS trades ({out_of_sample.trade_count} < {cfg.min_oos_trades})"
    if out_of_sample.sharpe < cfg.min_oos_sharpe:
        return False, (
            f"OOS Sharpe {out_of_sample.sharpe:.3f} < {cfg.min_oos_sharpe} "
            "(fails out-of-sample - in-sample-only / overfit)"
        )
    if in_sample.sharpe > 0 and out_of_sample.sharpe < cfg.overfit_oos_is_ratio * in_sample.sharpe:
        return False, (
            f"OOS Sharpe ({out_of_sample.sharpe:.3f}) collapses vs IS "
            f"({in_sample.sharpe:.3f}) - overfit"
        )
    if wf:
        positive = sum(1 for f in wf if f.metrics.sharpe > 0)
        if positive / len(wf) < cfg.min_walk_forward_positive_fraction:
            return False, f"walk-forward inconsistent ({positive}/{len(wf)} folds positive)"
    if mc.prob_positive_return < cfg.min_mc_prob_positive:
        return False, (
            f"Monte Carlo prob(+) {mc.prob_positive_return:.2f} < {cfg.min_mc_prob_positive}"
        )
    return True, "passed in-sample + out-of-sample + walk-forward + Monte Carlo"


def validate(
    strategy_cls: type[Strategy],
    bars: pd.DataFrame,
    param_grid: list[dict[str, Any]],
    bt: BacktestConfig,
    cfg: ValidationConfig,
    instrument: str = "",
) -> ValidationReport:
    """Run the full battery and return a pass/reject report with real metrics."""
    bars = bars.reset_index(drop=True)
    cut = int(len(bars) * (1.0 - cfg.oos_fraction))
    is_bars, oos_bars = bars.iloc[:cut], bars.iloc[cut:]

    best_params, is_metrics = recalibrate(strategy_cls, is_bars, param_grid, bt, cfg.min_oos_trades)
    oos_result = _run(strategy_cls(best_params), oos_bars, bt)
    wf = walk_forward(strategy_cls, bars, param_grid, bt, cfg.walk_forward_folds, cfg.min_oos_trades)
    mc = monte_carlo(oos_result.returns, cfg.monte_carlo_runs, bt.periods_per_year, cfg.monte_carlo_seed)
    passed, reason = _judge(is_metrics, oos_result.metrics, wf, mc, cfg)

    return ValidationReport(
        strategy_key=strategy_cls(best_params).key,
        instrument=instrument,
        best_params=best_params,
        in_sample=is_metrics,
        out_of_sample=oos_result.metrics,
        walk_forward=wf,
        monte_carlo=mc,
        passed=passed,
        reason=reason,
    )
