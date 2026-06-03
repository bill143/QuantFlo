#!/usr/bin/env python
"""Discover REAL candidate strategies/indicators from GitHub and persist them (gate B).

Runs Team 1 (Researchers) with the real GitHub search adapter over a set of queries,
scores + deduplicates the real hits, persists new candidates, and prints each with its
source URL, SPDX license, and relevance/novelty scores. No invented candidates.
Optional QUANTFLO_GITHUB_TOKEN / GITHUB_TOKEN raises the rate limit.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from quantflo.data.db import dispose_engine, session_scope
from quantflo.strategies.models import ResearchCandidate
from quantflo.teams.researchers import GitHubSearchProvider, Researcher

TENANT = "local"


async def main() -> int:
    researcher = Researcher(GitHubSearchProvider(), tenant=TENANT)
    try:
        new_ids = await researcher.discover(per_query=8)
    except Exception as exc:  # noqa: BLE001 - surface network/rate-limit errors plainly
        print(f"ERROR: GitHub search failed ({type(exc).__name__}: {exc}).")
        print("If rate-limited, set QUANTFLO_GITHUB_TOKEN and retry.")
        await dispose_engine()
        return 1

    print(f"discovered {len(new_ids)} new candidate(s)")
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ResearchCandidate)
                .where(ResearchCandidate.tenant_id == TENANT)
                .order_by(ResearchCandidate.relevance_score.desc())
                .limit(20)
            )
        ).scalars().all()
        print(f"\n=== research_candidates (top {len(rows)} by relevance) ===")
        for r in rows:
            license_label = r.license or "UNKNOWN"
            print(
                f"  rel={float(r.relevance_score):.2f} nov={float(r.novelty_score):.2f} "
                f"lic={license_label:<14} {r.title}"
            )
            print(f"        {r.source_url}")
    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
