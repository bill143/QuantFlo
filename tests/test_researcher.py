"""Researcher tests: scoring + dedup (pure) + persistence (fixture provider, tenant-isolated)."""
from __future__ import annotations

from sqlalchemy import delete, select

from quantflo.data.db import session_scope
from quantflo.strategies.models import ResearchCandidate
from quantflo.teams.researchers import (
    FixtureSearchProvider,
    Researcher,
    SearchHit,
    dedup_hash,
    novelty_score,
    relevance_score,
)
from tests.conftest import requires_db

_T = "pytest"
_HITS = [
    SearchHit(
        source_type="github", source_url="https://github.com/a/futures-bot",
        title="a/futures-bot", description="CME futures momentum trading strategy backtest",
        license="MIT", stars=100,
    ),
    SearchHit(
        source_type="github", source_url="https://github.com/b/web-framework",
        title="b/web-framework", description="a generic web framework", license="Apache-2.0", stars=9000,
    ),
    SearchHit(
        source_type="github", source_url="https://github.com/c/meanrev",
        title="c/meanrev", description="mean reversion indicator for S&P 500 futures",
        license="GPL-3.0", stars=30,
    ),
]


async def _purge() -> None:
    async with session_scope() as session:
        await session.execute(delete(ResearchCandidate).where(ResearchCandidate.tenant_id == _T))


def test_relevance_novelty_dedup_pure() -> None:
    assert relevance_score("CME futures backtest strategy", None) > 0.5
    assert relevance_score("a generic web framework", None) < 0.15
    assert novelty_score("foo bar baz", []) == 1.0
    assert novelty_score("futures momentum strategy", ["futures momentum strategy"]) == 0.0
    assert dedup_hash("https://github.com/A/B") == dedup_hash("https://github.com/a/b ")


@requires_db
async def test_researcher_persists_scored_and_deduped(pools: None) -> None:
    await _purge()
    researcher = Researcher(FixtureSearchProvider(_HITS), tenant=_T)

    first = await researcher.discover(["q"], per_query=10)
    assert len(first) == 2  # the low-relevance web framework is filtered out

    second = await researcher.discover(["q"], per_query=10)
    assert second == []  # everything deduped on the second pass

    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ResearchCandidate).where(ResearchCandidate.tenant_id == _T)
            )
        ).scalars().all()
        assert len(rows) == 2
        assert "GPL-3.0" in {row.license for row in rows}  # copyleft sample present for Creator
        assert all(float(row.relevance_score) >= 0.15 for row in rows)
        assert all(row.source_url.startswith("https://github.com/") for row in rows)

    await _purge()
