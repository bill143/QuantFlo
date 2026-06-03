"""Performance-metrics tests: validated against closed-form definitions (not freqtrade)."""
from __future__ import annotations

import math

import pandas as pd

from quantflo.backtest.metrics import (
    compute_metrics,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
)


def test_sharpe_matches_closed_form() -> None:
    returns = pd.Series([0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.005])
    expected = float(returns.mean() / returns.std(ddof=1)) * math.sqrt(252)
    assert abs(sharpe_ratio(returns, 252) - expected) < 1e-9


def test_sharpe_zero_variance_is_zero() -> None:
    assert sharpe_ratio(pd.Series([0.01, 0.01, 0.01]), 252) == 0.0


def test_max_drawdown_closed_form() -> None:
    equity = pd.Series([100, 110, 120, 90, 95, 130])
    assert abs(max_drawdown(equity) - (-0.25)) < 1e-9  # 120 -> 90


def test_profit_factor_and_win_rate() -> None:
    pnls = [100.0, -50.0, 200.0, -100.0]
    assert abs(profit_factor(pnls) - (300.0 / 150.0)) < 1e-9
    assert win_rate(pnls) == 0.5


def test_profit_factor_all_wins_is_inf() -> None:
    assert profit_factor([10.0, 20.0]) == math.inf


def test_sortino_penalizes_only_downside() -> None:
    returns = pd.Series([0.02, 0.03, -0.01, 0.01, -0.02, 0.04])
    assert sortino_ratio(returns, 252) > 0.0


def test_compute_metrics_assembles() -> None:
    returns = pd.Series([0.01, -0.005, 0.02])
    equity = pd.Series([100.0, 101.0, 100.5, 102.5])
    pnls = [50.0, -20.0, 30.0]
    m = compute_metrics(returns, equity, pnls, periods_per_year=252, years=0.25)
    assert m.trade_count == 3
    assert m.total_return == round(102.5 / 100.0 - 1.0, 8)
    assert set(m.as_dict()) == {
        "sharpe", "sortino", "calmar", "max_drawdown", "profit_factor",
        "win_rate", "avg_trade", "total_return", "trade_count",
    }
