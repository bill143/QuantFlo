"""Relevance / novelty scoring + dedup hashing for research candidates.

Deterministic heuristics: relevance weights futures/trading/indicator terminology in
the title+description; novelty is 1 minus the closest token-Jaccard similarity to any
already-seen candidate; the dedup hash is over the normalized source URL.
"""
from __future__ import annotations

import hashlib
import re

# term -> weight; relevance to the six CME index-futures instruments + strategy research.
_RELEVANCE_TERMS: dict[str, int] = {
    "futures": 3,
    "backtest": 3,
    "cme": 3,
    "e-mini": 3,
    "emini": 3,
    "trading strategy": 3,
    "strategy": 2,
    "indicator": 2,
    "quant": 2,
    "momentum": 2,
    "mean reversion": 2,
    "algorithmic": 2,
    "technical analysis": 2,
    "s&p 500": 2,
    "nasdaq": 2,
    "ohlc": 2,
    "signal": 1,
    "trading": 1,
}
_RELEVANCE_CAP = 12.0


def dedup_hash(source_url: str) -> str:
    return hashlib.sha256(source_url.strip().lower().encode()).hexdigest()[:64]


def relevance_score(title: str, description: str | None) -> float:
    text = f"{title} {description or ''}".lower()
    score = sum(weight for term, weight in _RELEVANCE_TERMS.items() if term in text)
    return round(min(1.0, score / _RELEVANCE_CAP), 4)


def _tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", text.lower()) if len(token) > 2}


def novelty_score(title: str, existing_titles: list[str]) -> float:
    target = _tokens(title)
    if not target or not existing_titles:
        return 1.0
    best_similarity = 0.0
    for other in existing_titles:
        other_tokens = _tokens(other)
        if not other_tokens:
            continue
        similarity = len(target & other_tokens) / len(target | other_tokens)
        best_similarity = max(best_similarity, similarity)
    return round(1.0 - best_similarity, 4)
