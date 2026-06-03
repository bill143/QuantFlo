"""Market-data provider abstraction (swappable vendor)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class MarketDataProvider(ABC):
    """Vendor-agnostic historical OHLCV source."""

    name: str

    @abstractmethod
    async def fetch_ohlcv(
        self, raw_symbol: str, timeframe: str, start: date, end: date
    ) -> pd.DataFrame:
        """Return normalized OHLCV for a per-contract symbol.

        Columns: ``time`` (tz-aware UTC), ``open/high/low/close`` (float), ``volume`` (int).
        ``end`` is exclusive (provider convention). Returns an empty frame if no data.
        """
