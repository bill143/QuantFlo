"""Canonical QUANTFLO team taxonomy — single source of truth.

Role text is the **verbatim Master Project Plan** role statement for each team.
Team keys, numbers, and names are stable and are asserted by the boot smoke test.
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
        "Researchers",
        "Continuously scan web, papers, repos, forums for new AI strategies/indicators. "
        "Score novelty and relevance to the six instruments. "
        "Hand qualified candidates to Creators.",
    ),
    TeamSpec(
        2,
        "creators",
        "Creators",
        "License/copyright compliance review, clean-room reimplementation against permissive "
        "licenses with attribution, then elevate to elite grade. Hand to Testers.",
    ),
    TeamSpec(
        3,
        "testers",
        "Testers",
        "Extended backtest + walk-forward + Monte Carlo + forward paper-test. "
        "Recalibrate parameters until aligned with current regime. "
        "Hand validated strategies to Traders.",
    ),
    TeamSpec(
        4,
        "traders",
        "Traders",
        "Autonomous execution within hard risk limits and human-authorized live gating.",
    ),
    TeamSpec(
        5,
        "orchestration",
        "Orchestration/Coordination",
        "The conductor. Manages handoffs, task queues, agent lifecycle, inter-team state "
        "across the ruflo swarm.",
    ),
    TeamSpec(
        6,
        "data_engineering",
        "Data Engineering",
        "Market data feeds, tick/bar ingestion, normalization, storage, feature pipelines. "
        "Garbage data = every downstream team fails.",
    ),
    TeamSpec(
        7,
        "risk_compliance",
        "Risk & Compliance",
        "Position sizing, drawdown limits, exposure caps, regulatory guardrails, "
        "pattern-day-trade and futures margin rules. Independent veto power over Traders.",
    ),
    TeamSpec(
        8,
        "modelops",
        "Continuous Learning / ModelOps",
        "Retraining, drift detection, model registry, versioning, champion/challenger promotion. "
        'This is your "continuous learning" mandate operationalized.',
    ),
    TeamSpec(
        9,
        "monitoring",
        "Monitoring & Observability",
        "Real-time health, latency, P&L attribution, alerting, the command-center "
        "dashboards/consoles.",
    ),
    TeamSpec(
        10,
        "governance",
        "Governance & Kill-Switch",
        "Hard stop authority, audit logging, human-authorization gates, circuit breakers. "
        "Sits above all teams.",
    ),
)


def team_count() -> int:
    """Number of canonical QUANTFLO teams."""
    return len(TEAMS)
