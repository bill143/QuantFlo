"""Smoke test: the swarm boots and registers exactly ten teams with correct roles.

This is the Phase 0 CI gate test. It imports the package and asserts the boot
path registers the ten canonical teams with their expected role keys/names.
"""
from __future__ import annotations

import quantflo
from quantflo.orchestration import AgentStatus, build_default_swarm

EXPECTED_TEAM_KEYS = {
    "researchers",
    "creators",
    "testers",
    "traders",
    "orchestration",
    "data_engineering",
    "risk_compliance",
    "modelops",
    "monitoring",
    "governance",
}

# Verbatim Master Project Plan team names (authoritative).
EXPECTED_TEAM_NAMES = {
    "researchers": "Researchers",
    "creators": "Creators",
    "testers": "Testers",
    "traders": "Traders",
    "orchestration": "Orchestration/Coordination",
    "data_engineering": "Data Engineering",
    "risk_compliance": "Risk & Compliance",
    "modelops": "Continuous Learning / ModelOps",
    "monitoring": "Monitoring & Observability",
    "governance": "Governance & Kill-Switch",
}


def test_package_imports() -> None:
    assert quantflo.__version__


def test_boot_registers_exactly_ten_teams() -> None:
    swarm = build_default_swarm()
    swarm.boot()
    agents = swarm.agents
    assert len(agents) == 10
    assert {a.key for a in agents} == EXPECTED_TEAM_KEYS


def test_team_names_match_taxonomy() -> None:
    swarm = build_default_swarm()
    actual = {a.key: a.name for a in swarm.agents}
    assert actual == EXPECTED_TEAM_NAMES


def test_team_numbers_are_one_through_ten() -> None:
    swarm = build_default_swarm()
    assert sorted(a.team_no for a in swarm.agents) == list(range(1, 11))


def test_all_agents_ready_after_boot() -> None:
    swarm = build_default_swarm()
    swarm.boot()
    assert all(a.status is AgentStatus.READY for a in swarm.agents)


def test_roles_are_nonempty() -> None:
    swarm = build_default_swarm()
    for agent in swarm.agents:
        assert agent.name.strip()
        assert agent.role.strip()
