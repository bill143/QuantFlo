"""EMA crossover — a reference strategy (original textbook logic, no port).

Long when the fast EMA is above the slow EMA, short when below, flat during warmup.
Pure signal logic used to exercise the framework, registry, and backtest engine.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from quantflo.strategies.base import Strategy


class EmaCrossover(Strategy):
    """Fast/slow EMA crossover. Emits target position in {-1, 0, +1}."""

    key = "ema_crossover"
    version = 1

    @classmethod
    def default_params(cls) -> dict[str, Any]:
        return {"fast": 8, "slow": 21}

    def generate_signals(
        self, bars: pd.DataFrame, features: pd.DataFrame | None = None
    ) -> pd.Series:
        fast_span = int(self.params["fast"])
        slow_span = int(self.params["slow"])
        close = pd.to_numeric(bars["close"]).reset_index(drop=True)
        fast = close.ewm(span=fast_span, adjust=False).mean()
        slow = close.ewm(span=slow_span, adjust=False).mean()
        signal = pd.Series(0, index=range(len(close)), dtype=int)
        signal[fast > slow] = 1
        signal[fast < slow] = -1
        signal.iloc[:slow_span] = 0  # warmup: smoothing not yet reliable
        return signal
