"""Market-data ingestion: provider -> roll-aware fetch -> quality gates -> persist.

For each instrument/timeframe the roll engine walks the continuous series; each
contract segment is fetched as REAL per-contract bars (tagged with its contract
code so the roll is visible in ``bars.contract``), quality-checked, then written.
Quality findings go to ``data_quality_events``; an ``ingestion_runs`` row audits
each run. Integrity-error bars are rejected (counted + recorded) — never silently
dropped. No trading logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quantflo.core.config import Settings, get_settings
from quantflo.core.instruments import INSTRUMENTS
from quantflo.data import roll
from quantflo.data.db import session_scope
from quantflo.data.models import Bar, DataQualityEvent, IngestionRun, Instrument
from quantflo.data.providers.base import MarketDataProvider
from quantflo.data.quality import QualityEvent, is_rth, run_quality_checks


@dataclass
class IngestionResult:
    """Outcome of ingesting one instrument/timeframe."""

    instrument: str
    timeframe: str
    rows_ingested: int
    rows_rejected: int
    quality_events: int
    contracts: list[str] = field(default_factory=list)


def _utc_midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


class Ingestor:
    """Roll-aware ingestion of real provider bars into the data layer."""

    def __init__(self, provider: MarketDataProvider, settings: Settings | None = None) -> None:
        self._provider = provider
        self._settings = settings or get_settings()
        self._tenant = self._settings.tenant_id

    async def ensure_instruments(self) -> dict[str, int]:
        """Upsert the six scope instruments; return ``{symbol: id}``."""
        ids: dict[str, int] = {}
        async with session_scope() as session:
            for symbol, spec in INSTRUMENTS.items():
                stmt = (
                    pg_insert(Instrument)
                    .values(
                        tenant_id=self._tenant,
                        symbol=spec.symbol,
                        name=spec.name,
                        exchange=spec.exchange.value,
                        tick_size=spec.tick_size,
                        point_value=spec.point_value,
                        currency=spec.currency,
                        is_micro=spec.is_micro,
                    )
                    .on_conflict_do_update(
                        index_elements=["tenant_id", "symbol"],
                        set_={
                            "name": spec.name,
                            "exchange": spec.exchange.value,
                            "tick_size": spec.tick_size,
                            "point_value": spec.point_value,
                            "is_micro": spec.is_micro,
                        },
                    )
                    .returning(Instrument.id)
                )
                ids[symbol] = (await session.execute(stmt)).scalar_one()
        return ids

    def contract_segments(
        self, symbol: str, start: date, end: date
    ) -> list[tuple[date, date, str, str]]:
        """``(seg_start, seg_end, contract_code, databento_symbol)`` per active contract."""
        segments: list[tuple[date, date, str, str]] = []
        cursor = start
        while cursor <= end:
            _, year, month = roll.active_contract_parts(cursor, symbol)
            seg_start = cursor
            while cursor <= end and roll.active_contract_parts(cursor, symbol)[1:] == (year, month):
                cursor += timedelta(days=1)
            seg_end = cursor - timedelta(days=1)
            segments.append(
                (
                    seg_start,
                    seg_end,
                    roll.contract_symbol(symbol, year, month),
                    roll.databento_raw_symbol(symbol, year, month),
                )
            )
        return segments

    async def ingest_instrument(
        self, symbol: str, timeframe: str, start: date, end: date, instrument_id: int
    ) -> IngestionResult:
        """Fetch, quality-check, and persist real bars for one instrument/timeframe."""
        run_id = await self._start_run(instrument_id, timeframe, start, end)
        try:
            frames: list[pd.DataFrame] = []
            contracts: list[str] = []
            for seg_start, seg_end, contract, raw in self.contract_segments(symbol, start, end):
                df = await self._provider.fetch_ohlcv(
                    raw, timeframe, seg_start, seg_end + timedelta(days=1)
                )
                if len(df) == 0:
                    continue
                df = df.copy()
                df["contract"] = contract
                frames.append(df)
                contracts.append(contract)

            if not frames:
                await self._finish_run(run_id, "success", 0, 0)
                return IngestionResult(symbol, timeframe, 0, 0, 0, contracts)

            full = pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)
            events = run_quality_checks(full, timeframe)
            reject_times = {e.bar_time for e in events if e.event_type == "ohlc_integrity"}
            keep = full[~full["time"].isin(reject_times)] if reject_times else full
            rejected = int(len(full) - len(keep))

            ingested = await self._write_bars(keep, instrument_id, timeframe)
            await self._write_events(events, instrument_id, timeframe, run_id)
            await self._finish_run(run_id, "success", ingested, rejected)
            return IngestionResult(symbol, timeframe, ingested, rejected, len(events), contracts)
        except Exception as exc:
            await self._finish_run(run_id, "failed", 0, 0, error=str(exc)[:500])
            raise

    async def _start_run(
        self, instrument_id: int, timeframe: str, start: date, end: date
    ) -> int:
        async with session_scope() as session:
            run = IngestionRun(
                tenant_id=self._tenant,
                provider=self._provider.name,
                instrument_id=instrument_id,
                timeframe=timeframe,
                start_date=_utc_midnight(start),
                end_date=_utc_midnight(end),
                status="running",
            )
            session.add(run)
            await session.flush()
            return run.id

    async def _finish_run(
        self, run_id: int, status: str, ingested: int, rejected: int, error: str | None = None
    ) -> None:
        async with session_scope() as session:
            await session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status=status,
                    rows_ingested=ingested,
                    rows_rejected=rejected,
                    finished_at=func.now(),
                    error=error,
                )
            )

    async def _write_bars(self, df: pd.DataFrame, instrument_id: int, timeframe: str) -> int:
        rows: list[dict[str, object]] = []
        for row in df.itertuples(index=False):
            ts = pd.Timestamp(row.time)
            rows.append(
                {
                    "tenant_id": self._tenant,
                    "instrument_id": instrument_id,
                    "timeframe": timeframe,
                    "contract": str(row.contract),
                    "time": ts.to_pydatetime(),
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": int(row.volume),
                    "source": self._provider.name,
                    "is_rth": is_rth(ts),
                }
            )
        if not rows:
            return 0
        async with session_scope() as session:
            stmt = pg_insert(Bar).values(rows).on_conflict_do_nothing(
                index_elements=["tenant_id", "instrument_id", "timeframe", "contract", "time"]
            )
            await session.execute(stmt)
        return len(rows)

    async def _write_events(
        self, events: list[QualityEvent], instrument_id: int, timeframe: str, run_id: int
    ) -> None:
        if not events:
            return
        rows: list[dict[str, object]] = []
        for event in events:
            bar_time = (
                pd.Timestamp(event.bar_time).to_pydatetime() if event.bar_time is not None else None
            )
            rows.append(
                {
                    "tenant_id": self._tenant,
                    "instrument_id": instrument_id,
                    "ingestion_run_id": run_id,
                    "timeframe": timeframe,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "bar_time": bar_time,
                    "detail": event.detail,
                }
            )
        async with session_scope() as session:
            await session.execute(pg_insert(DataQualityEvent).values(rows))
