"""Real Databento historical adapter (CME GLBX.MDP3, OHLCV schemas).

Uses raw-symbol per-contract requests (single-digit year, e.g. ``ESH4``) so the
roll engine selects which contract to fetch. Databento ``to_df()`` returns a frame
indexed by ``ts_event`` (tz-aware UTC) with float OHLC and integer volume.
"""
from __future__ import annotations

import asyncio
from datetime import date

import databento as db
import pandas as pd

from quantflo.data.providers.base import MarketDataProvider

_DATASET = "GLBX.MDP3"
_SCHEMA: dict[str, str] = {"1m": "ohlcv-1m", "1h": "ohlcv-1h", "1d": "ohlcv-1d"}
_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


class DatabentoProvider(MarketDataProvider):
    """Databento historical OHLCV for CME index futures."""

    name = "databento"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Databento API key required (QUANTFLO_DATABENTO_API_KEY)")
        self._client = db.Historical(api_key)

    async def fetch_ohlcv(
        self, raw_symbol: str, timeframe: str, start: date, end: date
    ) -> pd.DataFrame:
        if timeframe not in _SCHEMA:
            raise ValueError(f"unsupported timeframe: {timeframe!r}")
        schema = _SCHEMA[timeframe]

        def _query() -> pd.DataFrame:
            store = self._client.timeseries.get_range(
                dataset=_DATASET,
                symbols=[raw_symbol],
                schema=schema,
                stype_in="raw_symbol",
                start=start.isoformat(),
                end=end.isoformat(),
            )
            return store.to_df()

        raw = await asyncio.to_thread(_query)
        if raw is None or len(raw) == 0:
            return pd.DataFrame(columns=_COLUMNS)
        out = raw.reset_index().rename(columns={"ts_event": "time"})
        out = out[["time", "open", "high", "low", "close", "volume"]].copy()
        out["time"] = pd.to_datetime(out["time"], utc=True)
        return out
