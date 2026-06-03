"""Performance metrics for backtest evaluation.

CLEAN-ROOM reimplementation of freqtrade's (GPL-3.0) performance-metrics BEHAVIOR
from standard quantitative definitions — **no freqtrade source copied** (ADR 0005;
provenance: freqtrade source-probe ``✅ PASS @ 9eededca``). Formulas follow the
standard empyrical definitions (Sharpe / Sortino / Calmar / max-drawdown /
profit-factor) and are unit-tested against those closed forms, NOT against
freqtrade output.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class PerformanceMetrics:
    """A complete metric set for one evaluation."""

    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    profit_factor: float
    win_rate: float
    avg_trade: float
    total_return: float
    trade_count: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def sharpe_ratio(returns: pd.Series, periods_per_year: float, risk_free: float = 0.0) -> float:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 2:
        return 0.0
    excess = r - risk_free / periods_per_year
    sd = float(excess.std(ddof=1))
    if sd == 0.0:
        return 0.0
    return float(excess.mean() / sd * math.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, periods_per_year: float, risk_free: float = 0.0) -> float:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 2:
        return 0.0
    excess = r - risk_free / periods_per_year
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_dev = math.sqrt(float((downside**2).mean()))
    if downside_dev == 0.0:
        return 0.0
    return float(excess.mean() / downside_dev * math.sqrt(periods_per_year))


def max_drawdown(equity_curve: pd.Series) -> float:
    """Largest peak-to-trough decline as a fraction (<= 0)."""
    eq = pd.to_numeric(equity_curve, errors="coerce").dropna()
    if len(eq) < 2:
        return 0.0
    peak = eq.cummax()
    drawdown = (eq - peak) / peak
    return float(drawdown.min())


def profit_factor(trade_pnls: list[float]) -> float:
    gains = sum(p for p in trade_pnls if p > 0)
    losses = -sum(p for p in trade_pnls if p < 0)
    if losses == 0.0:
        return math.inf if gains > 0 else 0.0
    return float(gains / losses)


def win_rate(trade_pnls: list[float]) -> float:
    if not trade_pnls:
        return 0.0
    return sum(1 for p in trade_pnls if p > 0) / len(trade_pnls)


def calmar_ratio(total_return: float, max_dd: float, years: float) -> float:
    if max_dd == 0.0 or years <= 0.0 or total_return <= -1.0:
        return 0.0
    annual_return = (1.0 + total_return) ** (1.0 / years) - 1.0
    return float(annual_return / abs(max_dd))


def compute_metrics(
    returns: pd.Series,
    equity_curve: pd.Series,
    trade_pnls: list[float],
    periods_per_year: float,
    years: float,
) -> PerformanceMetrics:
    """Assemble the full metric set from bar returns, the equity curve, and trade PnLs."""
    total_return = (
        float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0) if len(equity_curve) >= 1 else 0.0
    )
    mdd = max_drawdown(equity_curve)
    pf = profit_factor(trade_pnls)
    return PerformanceMetrics(
        sharpe=round(sharpe_ratio(returns, periods_per_year), 8),
        sortino=round(sortino_ratio(returns, periods_per_year), 8),
        calmar=round(calmar_ratio(total_return, mdd, years), 8),
        max_drawdown=round(mdd, 8),
        profit_factor=round(pf, 8) if math.isfinite(pf) else pf,
        win_rate=round(win_rate(trade_pnls), 8),
        avg_trade=round(sum(trade_pnls) / len(trade_pnls), 8) if trade_pnls else 0.0,
        total_return=round(total_return, 8),
        trade_count=len(trade_pnls),
    )
