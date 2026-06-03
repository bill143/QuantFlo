"""Backtest engine tests: hand-computed buy&hold, commission, roll, execution lag."""
from __future__ import annotations

import pandas as pd

from quantflo.backtest.engine import BacktestConfig, Backtester


def _bars(prices: list[float], contracts: list[str] | None = None) -> pd.DataFrame:
    n = len(prices)
    contract_col = contracts if contracts is not None else ["C"] * n
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1] * n,
            "contract": contract_col,
        }
    )


def test_buy_and_hold_pnl_hand_computed_no_costs() -> None:
    bars = _bars([100.0, 101.0, 102.0, 103.0, 104.0])
    signals = pd.Series([1, 1, 1, 1, 1])
    cfg = BacktestConfig(
        point_value=1.0, tick_size=1.0, commission_per_contract=0.0,
        slippage_ticks=0.0, contracts=1, initial_capital=1000.0,
    )
    res = Backtester(cfg).run(bars, signals)
    # Enter long at bar1 open=101 (lag-1 from sig[0]); liquidate at 104 => +3.
    assert res.final_equity == 1003.0
    assert res.total_commission == 0.0
    assert res.trade_pnls == [3.0]


def test_commission_charged_both_sides() -> None:
    bars = _bars([100.0, 101.0, 102.0, 103.0, 104.0])
    cfg = BacktestConfig(
        point_value=1.0, tick_size=1.0, commission_per_contract=2.5,
        slippage_ticks=0.0, contracts=1, initial_capital=1000.0,
    )
    res = Backtester(cfg).run(bars, pd.Series([1, 1, 1, 1, 1]))
    assert res.final_equity == 998.0  # +3 gross - open(2.5) - close(2.5)
    assert res.total_commission == 5.0


def test_roll_closes_and_reopens_no_gap_pnl() -> None:
    # Contract changes A->B at bar2; the 101->102 cross-contract move must NOT be PnL.
    bars = _bars([100.0, 101.0, 102.0, 103.0], contracts=["A", "A", "B", "B"])
    cfg = BacktestConfig(
        point_value=1.0, tick_size=1.0, commission_per_contract=2.5,
        slippage_ticks=0.0, contracts=1, initial_capital=1000.0,
    )
    res = Backtester(cfg).run(bars, pd.Series([1, 1, 1, 1]))
    assert len(res.trade_pnls) == 2  # roll forces a close + reopen
    assert res.total_commission == 10.0  # 4 commissions
    assert res.trade_pnls[0] == -5.0  # roll trade is pure cost, no gap profit
    assert res.final_equity == 991.0


def test_flat_signal_no_trades() -> None:
    bars = _bars([100.0, 101.0, 102.0])
    cfg = BacktestConfig(point_value=1.0, tick_size=1.0, commission_per_contract=2.5)
    res = Backtester(cfg).run(bars, pd.Series([0, 0, 0]))
    assert res.trade_pnls == []
    assert res.final_equity == cfg.initial_capital


def test_signals_length_mismatch_raises() -> None:
    bars = _bars([100.0, 101.0, 102.0])
    cfg = BacktestConfig(point_value=1.0, tick_size=1.0)
    try:
        Backtester(cfg).run(bars, pd.Series([1, 1]))
    except ValueError:
        return
    raise AssertionError("expected ValueError on length mismatch")
