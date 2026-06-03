#!/usr/bin/env python
"""Run the Research -> Create -> Test pipeline end-to-end on the swarm bus (gate A).

Seeds 'create' tasks for a few real mappable candidates (discovered by Team 1),
drains them through Create -> Test with the REAL Tester, and prints the handoff
events from the state bus plus the registry rows at each stage and the pipeline
task statuses. No execution — signals + backtests only.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from quantflo.core.state_bus import BusMessage, InMemoryStateBus
from quantflo.data.db import dispose_engine, session_scope
from quantflo.orchestration import ResearchPipeline
from quantflo.strategies.models import (
    PipelineTask,
    ResearchCandidate,
    StrategyMetric,
    StrategyVersion,
)
from quantflo.teams.creators import Creator, map_to_template
from quantflo.teams.testers import Tester

TENANT = "local"
INSTRUMENT = "ES"
TIMEFRAME = "1h"
LIMIT = 3


async def main() -> int:
    bus = InMemoryStateBus()
    events: list[BusMessage] = []
    bus.subscribe("pipeline", events.append)
    pipeline = ResearchPipeline(Creator(TENANT), Tester(TENANT), bus, TENANT, INSTRUMENT, TIMEFRAME)

    async with session_scope() as session:
        candidates = (
            await session.execute(
                select(ResearchCandidate)
                .where(ResearchCandidate.tenant_id == TENANT, ResearchCandidate.status == "new")
                .order_by(ResearchCandidate.relevance_score.desc())
            )
        ).scalars().all()
    mappable = [c.id for c in candidates if map_to_template(c.title, c.description)][:LIMIT]
    print(f"seeding {len(mappable)} mappable candidate(s): {mappable}")

    seeded = await pipeline.seed_create_tasks(mappable)
    stats = await pipeline.run_pending()
    print(
        f"\nseeded={seeded} done={stats.done} retried={stats.retried} failed={stats.failed}\n"
        f"created versions={stats.created_versions} validated versions={stats.validated_versions}"
    )

    print("\n=== HANDOFF EVENTS (state bus, topic=pipeline) ===")
    for event in events:
        detail = {k: v for k, v in event.payload.items() if k != "event"}
        print(f"  [{event.source}] {event.payload['event']}: {detail}")

    print("\n=== REGISTRY at each stage (candidate -> version -> metrics) ===")
    async with session_scope() as session:
        for cid in mappable:
            candidate = (
                await session.execute(select(ResearchCandidate).where(ResearchCandidate.id == cid))
            ).scalar_one()
            print(f"  candidate {cid} [{candidate.status}] lic={candidate.license} {candidate.title}")
            versions = (
                await session.execute(
                    select(StrategyVersion).where(StrategyVersion.candidate_id == cid)
                )
            ).scalars().all()
            for v in versions:
                n_metrics = (
                    await session.execute(
                        select(StrategyMetric).where(StrategyMetric.strategy_version_id == v.id)
                    )
                ).scalars().all()
                print(
                    f"     -> version {v.id} {v.strategy_key} v{v.version} status={v.status} "
                    f"prov={v.license_provenance} champion={v.champion_status} metrics={len(n_metrics)}"
                )

        print("\n=== PIPELINE TASKS (idempotent, status-tracked) ===")
        tasks = (
            await session.execute(
                select(PipelineTask)
                .where(PipelineTask.tenant_id == TENANT)
                .order_by(PipelineTask.id)
            )
        ).scalars().all()
        for t in tasks:
            print(
                f"  task {t.id} stage={t.stage} status={t.status} "
                f"attempts={t.attempts} key={t.idempotency_key}"
            )
    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
