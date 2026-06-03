"""Research -> Create -> Test pipeline orchestration (Team 5).

Idempotent, retrying handoff of candidates through the create and test stages, backed
by the ``pipeline_tasks`` table (durable state, unique idempotency key) and the state
bus (handoff events). A candidate flows end-to-end with no manual intervention:
``create`` runs the Creator and, on success, enqueues a ``test`` task; ``test`` runs the
Tester. Failures retry up to ``max_attempts`` then mark the task failed. No execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quantflo.core.state_bus import BusMessage, StateBus
from quantflo.data.db import session_scope
from quantflo.strategies.models import PipelineTask, ResearchCandidate
from quantflo.teams.creators import Creator
from quantflo.teams.testers import Tester


@dataclass
class PipelineStats:
    seeded: int = 0
    done: int = 0
    retried: int = 0
    failed: int = 0
    created_versions: list[int] = field(default_factory=list)
    validated_versions: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class _ClaimedTask:
    id: int
    stage: str
    payload: dict[str, Any]
    attempts: int
    max_attempts: int


class ResearchPipeline:
    """Drain new candidates through Create -> Test, idempotently and with retries."""

    def __init__(
        self,
        creator: Creator,
        tester: Tester,
        state_bus: StateBus,
        tenant: str = "local",
        instrument: str = "ES",
        timeframe: str = "1h",
    ) -> None:
        self._creator = creator
        self._tester = tester
        self._bus = state_bus
        self._tenant = tenant
        self._instrument = instrument
        self._timeframe = timeframe

    def _publish(self, event: str, detail: dict[str, Any]) -> None:
        self._bus.publish(
            BusMessage(topic="pipeline", payload={"event": event, **detail}, source="orchestration")
        )

    async def _enqueue(
        self,
        stage: str,
        idempotency_key: str,
        payload: dict[str, Any],
        candidate_id: int | None = None,
        version_id: int | None = None,
    ) -> int | None:
        async with session_scope() as session:
            stmt = (
                pg_insert(PipelineTask)
                .values(
                    tenant_id=self._tenant, stage=stage, status="pending",
                    idempotency_key=idempotency_key, payload=payload,
                    candidate_id=candidate_id, strategy_version_id=version_id,
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
                .returning(PipelineTask.id)
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def seed_create_tasks(self, candidate_ids: list[int] | None = None) -> int:
        """Enqueue a 'create' task for each 'new' candidate (idempotent)."""
        async with session_scope() as session:
            query = select(ResearchCandidate.id).where(
                ResearchCandidate.tenant_id == self._tenant, ResearchCandidate.status == "new"
            )
            if candidate_ids is not None:
                query = query.where(ResearchCandidate.id.in_(candidate_ids))
            ids = [row.id for row in (await session.execute(query)).all()]
        seeded = 0
        for candidate_id in ids:
            task_id = await self._enqueue(
                "create", f"create:{candidate_id}", {"candidate_id": candidate_id},
                candidate_id=candidate_id,
            )
            if task_id is not None:
                seeded += 1
                self._publish("seeded", {"stage": "create", "candidate_id": candidate_id})
        return seeded

    async def _claim_next(self) -> _ClaimedTask | None:
        async with session_scope() as session:
            row = (
                await session.execute(
                    select(PipelineTask)
                    .where(PipelineTask.tenant_id == self._tenant, PipelineTask.status == "pending")
                    .order_by(PipelineTask.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            claimed = _ClaimedTask(
                id=row.id, stage=row.stage, payload=dict(row.payload),
                attempts=row.attempts, max_attempts=row.max_attempts,
            )
            row.status = "running"
            await session.flush()
        return claimed

    async def _mark(
        self, task_id: int, status: str, attempts: int | None = None, error: str | None = None
    ) -> None:
        values: dict[str, Any] = {"status": status}
        if attempts is not None:
            values["attempts"] = attempts
        if error is not None:
            values["error"] = error
        async with session_scope() as session:
            await session.execute(update(PipelineTask).where(PipelineTask.id == task_id).values(**values))

    async def _execute(self, task: _ClaimedTask, stats: PipelineStats) -> None:
        if task.stage == "create":
            candidate_id = int(task.payload["candidate_id"])
            outcome = await self._creator.create_from_candidate(candidate_id)
            if outcome.status == "created" and outcome.version_id is not None:
                stats.created_versions.append(outcome.version_id)
                self._publish(
                    "created",
                    {"candidate_id": candidate_id, "version_id": outcome.version_id,
                     "provenance": outcome.provenance},
                )
                await self._enqueue(
                    "test", f"test:{outcome.version_id}",
                    {"version_id": outcome.version_id, "instrument": self._instrument,
                     "timeframe": self._timeframe},
                    candidate_id=candidate_id, version_id=outcome.version_id,
                )
            else:
                self._publish("rejected_candidate", {"candidate_id": candidate_id, "reason": outcome.reason})
        elif task.stage == "test":
            version_id = int(task.payload["version_id"])
            instrument = str(task.payload.get("instrument", self._instrument))
            timeframe = str(task.payload.get("timeframe", self._timeframe))
            report = await self._tester.validate_version(version_id, instrument, timeframe)
            if report.passed:
                stats.validated_versions.append(version_id)
            self._publish(
                "tested",
                {"version_id": version_id, "passed": report.passed, "reason": report.reason},
            )
        else:
            raise ValueError(f"unknown pipeline stage: {task.stage}")

    async def run_pending(self, max_iterations: int = 500) -> PipelineStats:
        """Process pending tasks (create + test) to completion, with retries."""
        stats = PipelineStats()
        for _ in range(max_iterations):
            task = await self._claim_next()
            if task is None:
                break
            try:
                await self._execute(task, stats)
                await self._mark(task.id, "done")
                stats.done += 1
            except Exception as exc:  # noqa: BLE001 - stage failure -> retry/fail bookkeeping
                attempts = task.attempts + 1
                if attempts >= task.max_attempts:
                    await self._mark(task.id, "failed", attempts=attempts, error=str(exc)[:500])
                    stats.failed += 1
                    self._publish("task_failed", {"task_id": task.id, "stage": task.stage})
                else:
                    await self._mark(task.id, "pending", attempts=attempts, error=str(exc)[:500])
                    stats.retried += 1
        return stats
