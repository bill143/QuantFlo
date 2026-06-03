"""Strategy registry DB round-trip (tenant-isolated): candidate -> version -> metric -> task."""
from __future__ import annotations

from sqlalchemy import delete, select

from quantflo.data.db import session_scope
from quantflo.strategies.models import (
    PipelineTask,
    ResearchCandidate,
    StrategyMetric,
    StrategyVersion,
)
from tests.conftest import requires_db

_T = "pytest"


async def _purge() -> None:
    async with session_scope() as s:
        await s.execute(delete(PipelineTask).where(PipelineTask.tenant_id == _T))
        await s.execute(delete(StrategyMetric).where(StrategyMetric.tenant_id == _T))
        await s.execute(delete(StrategyVersion).where(StrategyVersion.tenant_id == _T))
        await s.execute(delete(ResearchCandidate).where(ResearchCandidate.tenant_id == _T))


@requires_db
async def test_registry_roundtrip(pools: None) -> None:
    await _purge()
    async with session_scope() as s:
        cand = ResearchCandidate(
            tenant_id=_T, source_type="github", source_url="https://github.com/x/y",
            title="Donchian breakout", license="MIT", dedup_hash="abc123", status="new",
        )
        s.add(cand)
        await s.flush()
        sv = StrategyVersion(
            tenant_id=_T, strategy_key="donchian", version=1, name="Donchian Breakout",
            candidate_id=cand.id, license="MIT", license_provenance="permissive_attribution",
            attribution="adapted from x/y (MIT)", status="created",
        )
        s.add(sv)
        await s.flush()
        s.add(StrategyMetric(
            tenant_id=_T, strategy_version_id=sv.id, evaluation_type="out_of_sample",
            instrument="ES", sharpe=1.23, trade_count=42,
        ))
        s.add(PipelineTask(
            tenant_id=_T, candidate_id=cand.id, strategy_version_id=sv.id,
            stage="test", status="done", idempotency_key="cand:1:test",
        ))

    async with session_scope() as s:
        sv = (
            await s.execute(select(StrategyVersion).where(StrategyVersion.tenant_id == _T))
        ).scalar_one()
        assert sv.status == "created"
        assert sv.license_provenance == "permissive_attribution"
        assert sv.champion_status == "none"  # server default
        metric = (
            await s.execute(select(StrategyMetric).where(StrategyMetric.tenant_id == _T))
        ).scalar_one()
        assert metric.evaluation_type == "out_of_sample" and metric.instrument == "ES"
        task = (
            await s.execute(select(PipelineTask).where(PipelineTask.tenant_id == _T))
        ).scalar_one()
        assert task.stage == "test" and task.status == "done"
        assert task.attempts == 0 and task.max_attempts == 3  # server defaults

    await _purge()
