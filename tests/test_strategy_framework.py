"""Strategy framework tests: EMA crossover emits valid signals (positions, never orders)."""
from __future__ import annotations

import pandas as pd
import pytest

from quantflo.strategies import SignalType, Strategy
from quantflo.strategies.library import EmaCrossover


def _trend_bars(n: int, slope: float) -> pd.DataFrame:
    close = [100.0 + slope * i for i in range(n)]
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": [1] * n}
    )


def test_signal_type_values() -> None:
    assert (int(SignalType.SHORT), int(SignalType.FLAT), int(SignalType.LONG)) == (-1, 0, 1)


def test_ema_crossover_emits_positions_in_range() -> None:
    sig = EmaCrossover().generate_signals(_trend_bars(120, slope=1.0))
    assert {int(v) for v in sig.unique()} <= {-1, 0, 1}
    assert len(sig) == 120
    assert (sig == 1).any()  # sustained uptrend -> long


def test_ema_crossover_short_on_downtrend() -> None:
    sig = EmaCrossover().generate_signals(_trend_bars(120, slope=-1.0))
    assert (sig == -1).any()


def test_params_merge_and_describe() -> None:
    s = EmaCrossover({"fast": 5})
    assert s.params == {"fast": 5, "slow": 21}
    assert s.describe() == {"key": "ema_crossover", "version": 1, "params": {"fast": 5, "slow": 21}}


def test_strategy_is_abstract() -> None:
    with pytest.raises(TypeError):
        Strategy()  # type: ignore[abstract]
