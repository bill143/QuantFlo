#!/usr/bin/env python
"""Run REAL Databento ingestion for the six scope instruments across timeframes.

Usage (Windows):  uv run python scripts/ingest_data.py
Requires QUANTFLO_DATABENTO_API_KEY in .env. Writes bars + data_quality_events +
ingestion_runs for [START, END] across TIMEFRAMES. No trading logic.
"""
from __future__ import annotations

import asyncio
from datetime import date

from quantflo.core.config import get_settings
from quantflo.core.instruments import all_symbols
from quantflo.data.db import dispose_engine
from quantflo.data.ingest import Ingestor
from quantflo.data.providers import DatabentoProvider

START = date(2024, 1, 1)
END = date(2024, 4, 30)
TIMEFRAMES = ("1d", "1h")


async def main() -> int:
    settings = get_settings()
    if not settings.databento_api_key:
        print("ERROR: QUANTFLO_DATABENTO_API_KEY is not set in .env")
        return 1
    ingestor = Ingestor(DatabentoProvider(settings.databento_api_key), settings)
    ids = await ingestor.ensure_instruments()
    print(f"instruments ensured: {ids}")
    try:
        for symbol in all_symbols():
            for timeframe in TIMEFRAMES:
                result = await ingestor.ingest_instrument(
                    symbol, timeframe, START, END, ids[symbol]
                )
                print(
                    f"{symbol:>4} {timeframe}: ingested={result.rows_ingested} "
                    f"rejected={result.rows_rejected} quality_events={result.quality_events} "
                    f"contracts={result.contracts}"
                )
    finally:
        await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
