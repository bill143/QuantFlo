"""SwarmConductor — registers team agents and drives the Phase 0 boot lifecycle.

This is the ruflo-facing orchestration skeleton (Team 5). It owns the agent
registry, a task queue, and a reference to the inter-team state bus. It contains
NO trading or strategy logic — only agent lifecycle and status reporting.
"""
from __future__ import annotations

from quantflo.core.state_bus import InMemoryStateBus, StateBus
from quantflo.orchestration.agent import AgentStatus, TeamAgent
from quantflo.orchestration.task_queue import TaskQueue
from quantflo.orchestration.teams import TEAMS, TeamSpec


class DuplicateTeamError(ValueError):
    """Raised when two agents register under the same team key."""


class SwarmConductor:
    """Coordinates registration and lifecycle of the ten QUANTFLO team agents."""

    def __init__(self, state_bus: StateBus | None = None) -> None:
        self._agents: dict[str, TeamAgent] = {}
        self.task_queue = TaskQueue()
        self.state_bus: StateBus = state_bus if state_bus is not None else InMemoryStateBus()

    def register(self, spec: TeamSpec) -> TeamAgent:
        """Register a single team as a swarm agent."""
        if spec.key in self._agents:
            raise DuplicateTeamError(spec.key)
        agent = TeamAgent(team_no=spec.team_no, key=spec.key, name=spec.name, role=spec.role)
        self._agents[spec.key] = agent
        self.state_bus.set_state("orchestration", f"agent:{spec.key}", agent.status.value)
        return agent

    def boot(self) -> None:
        """Initialize every registered agent to READY and record status on the bus."""
        for agent in self._agents.values():
            agent.initialize()
            self.state_bus.set_state("orchestration", f"agent:{agent.key}", agent.status.value)

    @property
    def agents(self) -> tuple[TeamAgent, ...]:
        """All registered agents, registration order preserved."""
        return tuple(self._agents.values())

    def status(self) -> dict[str, AgentStatus]:
        """Current lifecycle status per team key."""
        return {key: agent.status for key, agent in self._agents.items()}


def build_default_swarm(state_bus: StateBus | None = None) -> SwarmConductor:
    """Construct a conductor with all ten canonical teams registered (not yet booted)."""
    conductor = SwarmConductor(state_bus=state_bus)
    for spec in TEAMS:
        conductor.register(spec)
    return conductor
