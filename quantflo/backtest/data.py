"""Load the real continuous bar series for an instrument/timeframe from the data layer."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from quantflo.data.db import session_scope
from quantflo.data.models import Bar, Instrument


async def load_continuous_bars(
    instrument: str, timeframe: str, tenant: str = "local"
) -> pd.DataFrame:
    """Return the time-ordered continuous series (time/open/high/low/close/volume/contract).

    ``contract`` changes at each roll (as written by Phase-1 ingestion), so the backtest
    engine can roll the position per-contract.
    """
    stmt = (
        select(Bar.time, Bar.open, Bar.high, Bar.low, Bar.close, Bar.volume, Bar.contract)
        .join(Instrument, Instrument.id == Bar.instrument_id)
        .where(
            Instrument.symbol == instrument,
            Instrument.tenant_id == tenant,
            Bar.tenant_id == tenant,
            Bar.timeframe == timeframe,
        )
        .order_by(Bar.time)
    )
    async with session_scope() as session:
        rows = (await session.execute(stmt)).all()

    frame = pd.DataFrame(
        rows, columns=["time", "open", "high", "low", "close", "volume", "contract"]
    )
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame
