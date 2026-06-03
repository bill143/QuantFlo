"""Bias-detector tests: catch a planted lookahead + a non-converged (recursive) indicator."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from quantflo.backtest.bias import detect_lookahead_bias, detect_recursive_bias
from quantflo.strategies.base import Strategy
from quantflo.strategies.library import EmaCrossover


class _LookaheadStrategy(Strategy):
    """PLANTED lookahead: signal at t peeks at bar t+1 (must be flagged)."""

    key = "lookahead_trap"
    version = 1

    def generate_signals(self, bars: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.Series:
        close = pd.to_numeric(bars["close"]).reset_index(drop=True)
        future_move = close.shift(-1) - close  # peeks forward
        signal = pd.Series(0, index=range(len(close)), dtype=int)
        signal[future_move > 0] = 1
        signal[future_move < 0] = -1
        return signal.fillna(0).astype(int)


class _SmaStrategy(Strategy):
    """Non-recursive: SMA(window) needs only `window` bars -> startup-independent tail."""

    key = "sma_threshold"
    version = 1

    def generate_signals(self, bars: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.Series:
        close = pd.to_numeric(bars["close"]).reset_index(drop=True)
        sma = close.rolling(10).mean()
        signal = pd.Series(0, index=range(len(close)), dtype=int)
        signal[close > sma] = 1
        signal[close < sma] = -1
        return signal.fillna(0).astype(int)


def _wave_bars(n: int) -> pd.DataFrame:
    # Deterministic wavy series (no RNG) with frequent crossovers.
    close: list[float] = [100.0]
    for i in range(1, n):
        close.append(close[-1] + math.sin(i * 0.7) * 1.5 + math.cos(i * 0.31) * 0.9)
    series: dict[str, Any] = {
        "open": close, "high": close, "low": close, "close": close, "volume": [1] * n
    }
    return pd.DataFrame(series)


def test_lookahead_detector_flags_future_peek() -> None:
    result = detect_lookahead_bias(_LookaheadStrategy(), _wave_bars(200), cutoff=10)
    assert result.has_bias
    assert result.differing_signals >= 1


def test_lookahead_detector_passes_clean_strategy() -> None:
    result = detect_lookahead_bias(EmaCrossover(), _wave_bars(200), cutoff=10)
    assert not result.has_bias


def test_recursive_detector_flags_nonconverged_ema() -> None:
    # EMA(300) with a 20-bar startup is nowhere near converged -> tail depends on startup.
    strategy = EmaCrossover({"fast": 50, "slow": 300})
    result = detect_recursive_bias(strategy, _wave_bars(1400), startups=(20, 1100), compare_len=60)
    assert result.has_bias


def test_recursive_detector_passes_converged_sma() -> None:
    result = detect_recursive_bias(_SmaStrategy(), _wave_bars(1400), startups=(20, 1100), compare_len=60)
    assert not result.has_bias
