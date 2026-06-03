"""QUANTFLO orchestration package (Team 5 — ruflo swarm conductor).

Provides the agent registry, task queue, and swarm lifecycle skeleton. The
inter-team state bus contract lives in :mod:`quantflo.core.state_bus`.
"""
from __future__ import annotations

from quantflo.orchestration.agent import AgentStatus, TeamAgent
from quantflo.orchestration.pipeline import PipelineStats, ResearchPipeline
from quantflo.orchestration.swarm import (
    DuplicateTeamError,
    SwarmConductor,
    build_default_swarm,
)
from quantflo.orchestration.task_queue import Task, TaskQueue
from quantflo.orchestration.teams import TEAMS, TeamSpec, team_count

__all__ = [
    "TEAMS",
    "AgentStatus",
    "DuplicateTeamError",
    "PipelineStats",
    "ResearchPipeline",
    "SwarmConductor",
    "Task",
    "TaskQueue",
    "TeamAgent",
    "TeamSpec",
    "build_default_swarm",
    "team_count",
]
