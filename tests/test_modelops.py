"""ModelOps tests: champion/challenger promotion (validated-only) + drift detection."""
from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from quantflo.backtest.metrics import PerformanceMetrics
from quantflo.data.db import session_scope
from quantflo.strategies.models import StrategyMetric, StrategyVersion
from quantflo.teams.modelops import DriftDetector, ModelRegistry, SharpeDriftMetric
from tests.conftest import requires_db

_T = "pytest"


def _pm(sharpe: float) -> PerformanceMetrics:
    return PerformanceMetrics(sharpe, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)


def test_sharpe_drift_metric_pure() -> None:
    metric = SharpeDriftMetric(threshold=0.5)
    baseline = _pm(2.0)
    assert not metric.compute(baseline, _pm(1.8)).degraded  # (2.0-1.8)/2 = 0.10
    bad = metric.compute(baseline, _pm(0.2))  # (2.0-0.2)/2 = 0.90
    assert bad.degraded and bad.drift_score > 0.5


async def _purge() -> None:
    async with session_scope() as session:
        await session.execute(delete(StrategyMetric).where(StrategyMetric.tenant_id == _T))
        await session.execute(delete(StrategyVersion).where(StrategyVersion.tenant_id == _T))


async def _version(strategy_key: str, version: int, status: str = "validated",
                   champion: str = "challenger") -> int:
    async with session_scope() as session:
        row = StrategyVersion(
            tenant_id=_T, strategy_key=strategy_key, version=version, name=f"{strategy_key} v{version}",
            status=status, champion_status=champion, license_provenance="original",
        )
        session.add(row)
        await session.flush()
        return row.id


@requires_db
async def test_promote_champion_demotes_previous(pools: None) -> None:
    await _purge()
    v1 = await _version("ema_crossover", 1)
    v2 = await _version("ema_crossover", 2)
    registry = ModelRegistry(_T)

    await registry.promote_to_champion(v1)
    champion = await registry.current_champion("ema_crossover")
    assert champion is not None and champion.id == v1

    await registry.promote_to_champion(v2)  # must demote v1
    async with session_scope() as session:
        a = (await session.execute(select(StrategyVersion).where(StrategyVersion.id == v1))).scalar_one()
        b = (await session.execute(select(StrategyVersion).where(StrategyVersion.id == v2))).scalar_one()
        assert a.champion_status == "challenger" and b.champion_status == "champion"
    await _purge()


@requires_db
async def test_cannot_promote_rejected_strategy(pools: None) -> None:
    await _purge()
    vid = await _version("ema_crossover", 3, status="rejected", champion="none")
    with pytest.raises(ValueError):
        await ModelRegistry(_T).promote_to_champion(vid)  # no promotion on in-sample alone
    await _purge()


@requires_db
async def test_drift_detector_records_without_acting(pools: None) -> None:
    await _purge()
    vid = await _version("ema_crossover", 4)
    async with session_scope() as session:
        session.add(
            StrategyMetric(
                tenant_id=_T, strategy_version_id=vid, evaluation_type="out_of_sample",
                instrument="ES", sharpe=1.5, trade_count=20,
            )
        )

    result = await DriftDetector(tenant=_T).check(vid, _pm(0.2), instrument="ES")
    assert result.degraded  # (1.5-0.2)/1.5 = 0.867

    async with session_scope() as session:
        drift_rows = (
            await session.execute(
                select(StrategyMetric).where(
                    StrategyMetric.strategy_version_id == vid,
                    StrategyMetric.evaluation_type == "drift_check",
                )
            )
        ).scalars().all()
        assert len(drift_rows) == 1 and drift_rows[0].detail["degraded"] is True
        version = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.id == vid))
        ).scalar_one()
        assert version.champion_status == "challenger"  # unchanged: compute, don't act
    await _purge()
