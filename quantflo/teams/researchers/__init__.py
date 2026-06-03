"""Team 1 Research: real-source candidate discovery + relevance/novelty scoring."""
from __future__ import annotations

from quantflo.teams.researchers.researcher import DEFAULT_QUERIES, Researcher
from quantflo.teams.researchers.scoring import dedup_hash, novelty_score, relevance_score
from quantflo.teams.researchers.search import (
    FixtureSearchProvider,
    GitHubSearchProvider,
    SearchHit,
    SearchProvider,
)

__all__ = [
    "DEFAULT_QUERIES",
    "FixtureSearchProvider",
    "GitHubSearchProvider",
    "Researcher",
    "SearchHit",
    "SearchProvider",
    "dedup_hash",
    "novelty_score",
    "relevance_score",
]
