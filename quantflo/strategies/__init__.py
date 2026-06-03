"""QUANTFLO strategy framework + registry (Phase 2).

Strategies are pure signal logic (bars/features -> target position); the registry
records their versions, provenance, metrics, candidates, and pipeline tasks.
"""
from __future__ import annotations

from quantflo.strategies.base import SignalType, Strategy
from quantflo.strategies.models import (
    PipelineTask,
    ResearchCandidate,
    StrategyMetric,
    StrategyVersion,
)

__all__ = [
    "PipelineTask",
    "ResearchCandidate",
    "SignalType",
    "Strategy",
    "StrategyMetric",
    "StrategyVersion",
]
