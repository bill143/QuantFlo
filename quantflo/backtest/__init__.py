"""Backtest + evaluation toolkit (engine, metrics, bias detectors)."""
from __future__ import annotations

from quantflo.backtest.bias import (
    BiasResult,
    detect_lookahead_bias,
    detect_recursive_bias,
)
from quantflo.backtest.engine import BacktestConfig, Backtester, BacktestResult
from quantflo.backtest.metrics import (
    PerformanceMetrics,
    compute_metrics,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
)

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "Backtester",
    "BiasResult",
    "PerformanceMetrics",
    "compute_metrics",
    "detect_lookahead_bias",
    "detect_recursive_bias",
    "max_drawdown",
    "profit_factor",
    "sharpe_ratio",
    "sortino_ratio",
    "win_rate",
]
