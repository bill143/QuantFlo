"""Search providers for candidate discovery (vendor-agnostic + a real GitHub adapter).

The real :class:`GitHubSearchProvider` queries the GitHub REST API (stdlib ``urllib``,
no extra dependency) and returns REAL repositories with their URL and SPDX license.
A token (``QUANTFLO_GITHUB_TOKEN`` / ``GITHUB_TOKEN``) raises the rate limit but is
optional. Tests use :class:`FixtureSearchProvider` (recorded hits, no network).
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchHit:
    """A single discovered source (repo / paper)."""

    source_type: str
    source_url: str
    title: str
    description: str | None
    license: str | None
    stars: int = 0


class SearchProvider(ABC):
    """Vendor-agnostic source search."""

    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        """Return real hits for ``query`` (most-relevant first)."""


class GitHubSearchProvider(SearchProvider):
    """Real GitHub repository search (URL + SPDX license + stars)."""

    name = "github"
    _API = "https://api.github.com/search/repositories"

    def __init__(self, token: str | None = None) -> None:
        self._token = (
            token or os.environ.get("QUANTFLO_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
        )

    async def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        params = urllib.parse.urlencode(
            {"q": query, "per_page": str(min(limit, 50)), "sort": "stars", "order": "desc"}
        )
        data = await asyncio.to_thread(self._get, f"{self._API}?{params}")
        hits: list[SearchHit] = []
        for item in data.get("items", [])[:limit]:
            license_obj = item.get("license") or {}
            hits.append(
                SearchHit(
                    source_type="github",
                    source_url=str(item["html_url"]),
                    title=str(item["full_name"]),
                    description=item.get("description"),
                    license=license_obj.get("spdx_id"),
                    stars=int(item.get("stargazers_count", 0)),
                )
            )
        return hits

    def _get(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(  # noqa: S310 - fixed https GitHub API host
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "quantflo-researcher",
            },
        )
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            payload: dict[str, Any] = json.loads(response.read().decode())
        return payload


class FixtureSearchProvider(SearchProvider):
    """Recorded hits for tests (no network)."""

    name = "fixture"

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    async def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        return self._hits[:limit]
