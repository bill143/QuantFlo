"""ATR (Average True Range) — a volatility feature. Math on bars, no trading logic."""
from __future__ import annotations

import pandas as pd

from quantflo.data.features.base import Feature


class ATR(Feature):
    """Wilder's Average True Range over ``period`` bars.

    TR_t = max(high-low, |high-prev_close|, |low-prev_close|); ATR is Wilder's RMA
    (recursive moving average, alpha = 1/period) of TR.
    """

    def __init__(self, period: int = 14) -> None:
        if period < 1:
            raise ValueError("ATR period must be >= 1")
        self.period = period
        self.name = f"atr_{period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high = pd.to_numeric(df["high"])
        low = pd.to_numeric(df["low"])
        close = pd.to_numeric(df["close"])
        prev_close = close.shift(1)
        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / self.period, adjust=False, min_periods=self.period).mean()
        atr.name = self.name
        return atr
