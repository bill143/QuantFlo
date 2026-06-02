"""Team agent abstraction and lifecycle for the QUANTFLO swarm."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentStatus(StrEnum):
    """Lifecycle states a team agent moves through during a swarm boot."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(slots=True)
class TeamAgent:
    """A registrable swarm agent representing one QUANTFLO team.

    Phase 0 carries identity, role, and lifecycle status only. Team-internal
    behaviour (research, strategy creation, execution, ...) is intentionally
    absent and is filled in by later phases.
    """

    team_no: int
    key: str
    name: str
    role: str
    status: AgentStatus = AgentStatus.REGISTERED

    def initialize(self) -> None:
        """Advance REGISTERED -> INITIALIZING -> READY.

        No business logic: this only advances lifecycle state so the conductor
        can prove every team is wired and bootable.
        """
        self.status = AgentStatus.INITIALIZING
        self.status = AgentStatus.READY

    def stop(self) -> None:
        """Move the agent to STOPPED."""
        self.status = AgentStatus.STOPPED
