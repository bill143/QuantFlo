"""Backtest + evaluation toolkit (metrics, bias detectors; engine added in Phase 2)."""
from __future__ import annotations

from quantflo.backtest.bias import (
    BiasResult,
    detect_lookahead_bias,
    detect_recursive_bias,
)
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
