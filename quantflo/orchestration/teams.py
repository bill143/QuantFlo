"""Canonical QUANTFLO team taxonomy — single source of truth.

Role text here is synthesized from the QUANTFLO team descriptors and is pending
reconciliation with the verbatim Master Project Plan role statements (tracked as
a known gap in the Phase 0 gate report). The team keys, numbers, and names are
stable and are asserted by the boot smoke test.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeamSpec:
    """Declarative spec for one team agent."""

    team_no: int
    key: str
    name: str
    role: str


TEAMS: tuple[TeamSpec, ...] = (
    TeamSpec(
        1,
        "researchers",
        "Research Team",
        "Market research, hypothesis generation, and signal discovery for CME index futures.",
    ),
    TeamSpec(
        2,
        "creators",
        "Strategy Creation Team",
        "Translate validated research into candidate strategy specifications.",
    ),
    TeamSpec(
        3,
        "testers",
        "Testing & Validation Team",
        "Backtest, walk-forward, and statistically validate candidate strategies.",
    ),
    TeamSpec(
        4,
        "traders",
        "Trading Team",
        "Route validated strategies to execution and manage the order lifecycle.",
    ),
    TeamSpec(
        5,
        "orchestration",
        "Orchestration Team",
        "ruflo swarm conductor: coordinates all teams, task routing, and lifecycle.",
    ),
    TeamSpec(
        6,
        "data_engineering",
        "Data Engineering Team",
        "Market-data ingestion, normalization, storage, and feature pipelines.",
    ),
    TeamSpec(
        7,
        "risk_compliance",
        "Risk & Compliance Team",
        "Pre-trade and post-trade risk limits, exposure control, and compliance.",
    ),
    TeamSpec(
        8,
        "modelops",
        "ModelOps Team",
        "Continuous learning: model training, evaluation, deployment, and drift monitoring.",
    ),
    TeamSpec(
        9,
        "monitoring",
        "Monitoring Team",
        "Observability: system health, latency, P&L, and alerting.",
    ),
    TeamSpec(
        10,
        "governance",
        "Governance Team",
        "Kill-switch authority, change control, and final go/no-go gates.",
    ),
)


def team_count() -> int:
    """Number of canonical QUANTFLO teams."""
    return len(TEAMS)
