"""Ingestion-pipeline test with a fake provider (no network); isolated to tenant 'pytest'.

This exercises the ingestion *logic* (roll-aware fetch, quality gating, rejection,
persistence) without hitting Databento. The real-data run (scripts/ingest_data.py)
is the gate-B evidence; this guards the pipeline in CI.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import delete, func, select

from quantflo.core.config import get_settings
from quantflo.data.db import session_scope
from quantflo.data.ingest import Ingestor
from quantflo.data.models import Bar, DataQualityEvent
from quantflo.data.providers.base import MarketDataProvider
from tests.conftest import requires_db

_TEST_TENANT = "pytest"


class _FakeProvider(MarketDataProvider):
    name = "fake"

    async def fetch_ohlcv(
        self, raw_symbol: str, timeframe: str, start: date, end: date
    ) -> pd.DataFrame:
        # 3 daily bars; the 3rd is malformed (low > high) to exercise rejection.
        return pd.DataFrame(
            {
                "time": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"], utc=True),
                "open": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 104.0],  # 3rd bar: low > high -> integrity error
                "close": [100.5, 101.5, 102.5],
                "volume": [10, 11, 12],
            }
        )


@requires_db
async def test_ingest_pipeline_persists_and_rejects_bad_bars(pools: None) -> None:
    settings = get_settings().model_copy(update={"tenant_id": _TEST_TENANT})
    ingestor = Ingestor(_FakeProvider(), settings)
    ids = await ingestor.ensure_instruments()
    es_id = ids["ES"]

    async with session_scope() as session:
        await session.execute(
            delete(Bar).where(Bar.tenant_id == _TEST_TENANT, Bar.instrument_id == es_id)
        )

    result = await ingestor.ingest_instrument("ES", "1d", date(2024, 1, 1), date(2024, 1, 5), es_id)
    assert result.rows_rejected == 1
    assert result.rows_ingested == 2
    assert "ESH24" in result.contracts

    async with session_scope() as session:
        bar_count = (
            await session.execute(
                select(func.count())
                .select_from(Bar)
                .where(Bar.tenant_id == _TEST_TENANT, Bar.instrument_id == es_id)
            )
        ).scalar_one()
        assert bar_count == 2
        event_count = (
            await session.execute(
                select(func.count())
                .select_from(DataQualityEvent)
                .where(
                    DataQualityEvent.tenant_id == _TEST_TENANT,
                    DataQualityEvent.event_type == "ohlc_integrity",
                )
            )
        ).scalar_one()
        assert event_count >= 1

        # cleanup test rows
        await session.execute(
            delete(DataQualityEvent).where(DataQualityEvent.tenant_id == _TEST_TENANT)
        )
        await session.execute(delete(Bar).where(Bar.tenant_id == _TEST_TENANT))
