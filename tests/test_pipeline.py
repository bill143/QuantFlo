"""Pipeline orchestration test: end-to-end Create->Test, idempotent + retries (tenant-isolated)."""
from __future__ import annotations

from sqlalchemy import delete, select, update

from quantflo.backtest.metrics import PerformanceMetrics
from quantflo.backtest.validation import MonteCarloSummary, ValidationReport
from quantflo.core.state_bus import BusMessage, InMemoryStateBus
from quantflo.data.db import session_scope
from quantflo.orchestration import ResearchPipeline
from quantflo.strategies.models import PipelineTask, ResearchCandidate, StrategyVersion
from quantflo.teams.creators import Creator
from quantflo.teams.testers import Tester as _BaseTester
from tests.conftest import requires_db

_T = "pytest"
_ZERO = PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
_MC = MonteCarloSummary(0, 0.0, 0.0, 0.0, 0.0)


def _report(passed: bool) -> ValidationReport:
    return ValidationReport("ema_crossover", "ES", {}, _ZERO, _ZERO, [], _MC, passed, "stub")


class _StubTester(_BaseTester):
    async def validate_version(self, version_id: int, instrument: str, timeframe: str) -> ValidationReport:
        async with session_scope() as session:
            await session.execute(
                update(StrategyVersion)
                .where(StrategyVersion.id == version_id)
                .values(status="validated", champion_status="challenger")
            )
        return _report(True)


class _FailingTester(_BaseTester):
    async def validate_version(self, version_id: int, instrument: str, timeframe: str) -> ValidationReport:
        raise RuntimeError("boom")


async def _purge() -> None:
    async with session_scope() as session:
        await session.execute(delete(PipelineTask).where(PipelineTask.tenant_id == _T))
        await session.execute(delete(StrategyVersion).where(StrategyVersion.tenant_id == _T))
        await session.execute(delete(ResearchCandidate).where(ResearchCandidate.tenant_id == _T))


async def _new_candidate(title: str, license_spdx: str, description: str, digest: str) -> int:
    async with session_scope() as session:
        candidate = ResearchCandidate(
            tenant_id=_T, source_type="github", source_url=f"https://github.com/x/{digest}",
            title=title, description=description, license=license_spdx, dedup_hash=digest, status="new",
        )
        session.add(candidate)
        await session.flush()
        return candidate.id


@requires_db
async def test_pipeline_end_to_end_idempotent(pools: None) -> None:
    await _purge()
    cid = await _new_candidate("gpl momentum crossover", "GPL-3.0", "momentum crossover", "h1")
    bus = InMemoryStateBus()
    events: list[BusMessage] = []
    bus.subscribe("pipeline", events.append)
    pipeline = ResearchPipeline(Creator(_T), _StubTester(_T), bus, tenant=_T)

    assert await pipeline.seed_create_tasks() == 1
    stats = await pipeline.run_pending()
    assert stats.done == 2  # create + test
    assert len(stats.created_versions) == 1 and len(stats.validated_versions) == 1

    async with session_scope() as session:
        candidate = (
            await session.execute(select(ResearchCandidate).where(ResearchCandidate.id == cid))
        ).scalar_one()
        assert candidate.status == "created"
        version = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.candidate_id == cid))
        ).scalar_one()
        assert version.status == "validated" and version.champion_status == "challenger"
        assert version.license_provenance == "clean_room"  # GPL flowed through as clean-room
        tasks = (
            await session.execute(select(PipelineTask).where(PipelineTask.tenant_id == _T))
        ).scalars().all()
        assert len(tasks) == 2 and {t.status for t in tasks} == {"done"}

    kinds = [e.payload["event"] for e in events]
    assert "seeded" in kinds and "created" in kinds and "tested" in kinds

    # Idempotent: re-seed + re-run are no-ops.
    assert await pipeline.seed_create_tasks() == 0
    assert (await pipeline.run_pending()).done == 0
    await _purge()


@requires_db
async def test_pipeline_retries_then_fails(pools: None) -> None:
    await _purge()
    await _new_candidate("ema trend follow", "MIT", "ema trend", "h2")
    pipeline = ResearchPipeline(Creator(_T), _FailingTester(_T), InMemoryStateBus(), tenant=_T)
    await pipeline.seed_create_tasks()
    stats = await pipeline.run_pending()
    assert stats.failed == 1 and stats.retried == 2  # test stage fails 3x -> failed

    async with session_scope() as session:
        test_task = (
            await session.execute(
                select(PipelineTask).where(PipelineTask.tenant_id == _T, PipelineTask.stage == "test")
            )
        ).scalar_one()
        assert test_task.status == "failed" and test_task.attempts == 3
    await _purge()
