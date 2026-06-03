"""Tester integration test: validate a version against REAL ES bars; persist metrics + verdict."""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from quantflo.data.db import session_scope
from quantflo.strategies.models import StrategyMetric, StrategyVersion
from quantflo.teams.testers import Tester as StrategyTester
from tests.conftest import requires_db

_KEY = "ema_crossover"
_VER = 999  # throwaway version, does not collide with the gate-D run (1..6)


async def _purge(version_id: int | None) -> None:
    async with session_scope() as session:
        if version_id is not None:
            await session.execute(
                delete(StrategyMetric).where(StrategyMetric.strategy_version_id == version_id)
            )
        await session.execute(
            delete(StrategyVersion).where(
                StrategyVersion.strategy_key == _KEY, StrategyVersion.version == _VER
            )
        )


@requires_db
async def test_tester_validates_real_bars_and_persists(pools: None) -> None:
    await _purge(None)
    async with session_scope() as session:
        version = StrategyVersion(
            tenant_id="local", strategy_key=_KEY, version=_VER, name="EMA test",
            status="created", license_provenance="original",
        )
        session.add(version)
        await session.flush()
        version_id = version.id

    try:
        report = await StrategyTester(tenant="local").validate_version(version_id, "ES", "1h")
    except ValueError as exc:
        if "insufficient bars" in str(exc):
            await _purge(version_id)
            pytest.skip("no real bars in DB (run scripts/ingest_data.py) - local integration test")
        raise
    assert report.out_of_sample.trade_count >= 0  # real numbers, any sign

    async with session_scope() as session:
        metrics = (
            await session.execute(
                select(StrategyMetric).where(StrategyMetric.strategy_version_id == version_id)
            )
        ).scalars().all()
        types = {m.evaluation_type for m in metrics}
        assert {"in_sample", "out_of_sample", "monte_carlo"} <= types

        version = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.id == version_id))
        ).scalar_one()
        assert version.status in ("validated", "rejected")
        if version.status == "validated":
            assert version.champion_status == "challenger"
        else:
            assert version.rejection_reason

        in_m = next(m for m in metrics if m.evaluation_type == "in_sample")
        oos_m = next(m for m in metrics if m.evaluation_type == "out_of_sample")
        assert in_m.window_end is not None and oos_m.window_start is not None
        assert oos_m.window_start > in_m.window_end  # OOS window distinct from IS window

    await _purge(version_id)
