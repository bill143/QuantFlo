"""Team 1 (Researchers): discover real candidate strategies/indicators from real sources.

Runs a :class:`SearchProvider` over a set of queries, scores each real hit for relevance
and novelty against the six instruments, deduplicates (against the DB and within the
batch), and persists new scored candidates to ``research_candidates`` (status ``new``).
No invented candidates — every row carries the source URL, license, and scores.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quantflo.data.db import session_scope
from quantflo.strategies.models import ResearchCandidate
from quantflo.teams.researchers.scoring import dedup_hash, novelty_score, relevance_score
from quantflo.teams.researchers.search import SearchHit, SearchProvider

DEFAULT_QUERIES = [
    "CME futures trading strategy python",
    "momentum indicator backtest",
    "mean reversion futures strategy",
    "technical analysis trading signals python",
]
_MIN_RELEVANCE = 0.15


class Researcher:
    """Discover, score, deduplicate, and persist research candidates."""

    def __init__(
        self, provider: SearchProvider, tenant: str = "local", min_relevance: float = _MIN_RELEVANCE
    ) -> None:
        self._provider = provider
        self._tenant = tenant
        self._min_relevance = min_relevance

    async def discover(self, queries: list[str] | None = None, per_query: int = 20) -> list[int]:
        """Discover candidates for ``queries``; return the ids of newly-persisted rows."""
        queries = queries or DEFAULT_QUERIES
        existing_hashes, existing_titles = await self._existing()
        batch_hashes: set[str] = set()
        new_ids: list[int] = []

        for query in queries:
            for hit in await self._provider.search(query, per_query):
                digest = dedup_hash(hit.source_url)
                if digest in existing_hashes or digest in batch_hashes:
                    continue
                batch_hashes.add(digest)
                relevance = relevance_score(hit.title, hit.description)
                if relevance < self._min_relevance:
                    continue
                novelty = novelty_score(hit.title, existing_titles)
                candidate_id = await self._persist(hit, digest, relevance, novelty)
                if candidate_id is not None:
                    new_ids.append(candidate_id)
                    existing_titles.append(hit.title)
        return new_ids

    async def _existing(self) -> tuple[set[str], list[str]]:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(ResearchCandidate.dedup_hash, ResearchCandidate.title).where(
                        ResearchCandidate.tenant_id == self._tenant
                    )
                )
            ).all()
        return {r.dedup_hash for r in rows}, [r.title for r in rows]

    async def _persist(
        self, hit: SearchHit, digest: str, relevance: float, novelty: float
    ) -> int | None:
        async with session_scope() as session:
            stmt = (
                pg_insert(ResearchCandidate)
                .values(
                    tenant_id=self._tenant,
                    source_type=hit.source_type,
                    source_url=hit.source_url[:512],
                    title=hit.title[:512],
                    description=(hit.description or None),
                    license=hit.license,
                    relevance_score=relevance,
                    novelty_score=novelty,
                    dedup_hash=digest,
                    status="new",
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "dedup_hash"])
                .returning(ResearchCandidate.id)
            )
            result = (await session.execute(stmt)).scalar_one_or_none()
        return result
