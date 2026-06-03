"""Validation-battery tests: overfit REJECTED, robust PASSES, Monte-Carlo mechanics."""
from __future__ import annotations

import math

import pandas as pd

from quantflo.backtest.engine import BacktestConfig
from quantflo.backtest.validation import ValidationConfig, monte_carlo, validate
from quantflo.strategies.library import EmaCrossover

_GRID = [{"fast": f, "slow": s} for f in (5, 8, 13) for s in (21, 34, 55) if f < s]
_BT = BacktestConfig(
    point_value=1.0, tick_size=0.25, commission_per_contract=0.5,
    slippage_ticks=1.0, contracts=1, initial_capital=100_000.0, periods_per_year=252.0,
)


def _bars(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame(
        {
            "time": pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC"),
            "open": closes, "high": closes, "low": closes, "close": closes,
            "volume": [1] * n, "contract": ["C"] * n,
        }
    )


def _oscillating_uptrend(n: int, drift: float, amp: float, period: float) -> list[float]:
    return [100.0 + drift * i + amp * math.sin(i * 2 * math.pi / period) for i in range(n)]


def _whipsaw(n: int, amp: float) -> list[float]:
    return [100.0 + amp * math.sin(i * 2 * math.pi / 4.0) for i in range(n)]  # choppy, no drift


def test_robust_strategy_passes() -> None:
    # Slow, sustained swings (period 120) that an EMA crossover rides profitably in
    # both the in-sample and held-out windows -> passes the full battery.
    report = validate(
        EmaCrossover, _bars(_oscillating_uptrend(1200, 0.02, 40.0, 120)), _GRID,
        _BT, ValidationConfig(), instrument="ES",
    )
    assert report.passed, report.reason
    assert report.out_of_sample.trade_count >= 5


def test_overfit_strategy_rejected() -> None:
    # IS = profitable oscillating uptrend; OOS = pure whipsaw (no trend) -> OOS fails.
    closes = _oscillating_uptrend(630, 0.25, 8.0, 40) + _whipsaw(270, 6.0)
    report = validate(
        EmaCrossover, _bars(closes), _GRID, _BT, ValidationConfig(), instrument="ES"
    )
    assert not report.passed
    assert "OOS" in report.reason or "overfit" in report.reason.lower()


def test_monte_carlo_summary_ordered() -> None:
    returns = pd.Series([0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.005] * 30)
    mc = monte_carlo(returns, runs=200, periods_per_year=252.0, seed=7)
    assert mc.runs == 200
    assert 0.0 <= mc.prob_positive_return <= 1.0
    assert mc.sharpe_p05 <= mc.sharpe_p50 <= mc.sharpe_p95
