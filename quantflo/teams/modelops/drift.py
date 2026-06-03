"""Team 8 (ModelOps): drift detection interface + one real metric.

Compute, don't act: the detector measures whether a validated strategy's RECENT
backtest metrics have degraded versus its validation baseline (the out-of-sample
metrics recorded by the Tester), records a ``drift_check`` row, and returns the result.
Acting on drift (retraining, demotion, retirement) is a later phase.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from quantflo.backtest.metrics import PerformanceMetrics
from quantflo.data.db import session_scope
from quantflo.strategies.models import StrategyMetric


@dataclass(frozen=True)
class DriftResult:
    metric: str
    drift_score: float  # positive => degradation vs baseline
    degraded: bool
    detail: dict[str, Any]


class DriftMetric(ABC):
    """A drift measure comparing baseline vs recent performance."""

    name: str

    @abstractmethod
    def compute(self, baseline: PerformanceMetrics, recent: PerformanceMetrics) -> DriftResult:
        ...


class SharpeDriftMetric(DriftMetric):
    """Relative Sharpe degradation: ``(baseline - recent) / |baseline|``."""

    name = "sharpe_drift"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def compute(self, baseline: PerformanceMetrics, recent: PerformanceMetrics) -> DriftResult:
        denom = abs(baseline.sharpe) if abs(baseline.sharpe) > 1e-9 else 1.0
        drift = (baseline.sharpe - recent.sharpe) / denom
        return DriftResult(
            metric=self.name,
            drift_score=round(drift, 6),
            degraded=drift > self.threshold,
            detail={
                "baseline_sharpe": baseline.sharpe,
                "recent_sharpe": recent.sharpe,
                "threshold": self.threshold,
            },
        )


def _to_metrics(row: StrategyMetric) -> PerformanceMetrics:
    return PerformanceMetrics(
        sharpe=float(row.sharpe or 0.0),
        sortino=float(row.sortino or 0.0),
        calmar=0.0,
        max_drawdown=float(row.max_drawdown or 0.0),
        profit_factor=float(row.profit_factor or 0.0),
        win_rate=float(row.win_rate or 0.0),
        avg_trade=float(row.avg_trade or 0.0),
        total_return=float(row.total_return or 0.0),
        trade_count=int(row.trade_count),
    )


class DriftDetector:
    """Compute drift vs a version's validation baseline; record it (no action taken)."""

    def __init__(self, metric: DriftMetric | None = None, tenant: str = "local") -> None:
        self._metric = metric or SharpeDriftMetric()
        self._tenant = tenant

    async def check(
        self, version_id: int, recent: PerformanceMetrics, instrument: str | None = None
    ) -> DriftResult:
        baseline = await self._load_baseline(version_id, instrument)
        result = self._metric.compute(baseline, recent)
        await self._record(version_id, instrument, recent, result)
        return result

    async def _load_baseline(self, version_id: int, instrument: str | None) -> PerformanceMetrics:
        async with session_scope() as session:
            query = select(StrategyMetric).where(
                StrategyMetric.strategy_version_id == version_id,
                StrategyMetric.evaluation_type == "out_of_sample",
            )
            if instrument is not None:
                query = query.where(StrategyMetric.instrument == instrument)
            row = (
                await session.execute(query.order_by(StrategyMetric.created_at.desc()).limit(1))
            ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"no out_of_sample baseline metric for version {version_id}")
        return _to_metrics(row)

    async def _record(
        self,
        version_id: int,
        instrument: str | None,
        recent: PerformanceMetrics,
        result: DriftResult,
    ) -> None:
        async with session_scope() as session:
            session.add(
                StrategyMetric(
                    tenant_id=self._tenant,
                    strategy_version_id=version_id,
                    evaluation_type="drift_check",
                    instrument=instrument,
                    sharpe=recent.sharpe,
                    detail={
                        "metric": result.metric,
                        "drift_score": result.drift_score,
                        "degraded": result.degraded,
                        **result.detail,
                    },
                )
            )
