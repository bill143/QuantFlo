"""Team 8 (ModelOps): champion/challenger management over the strategy registry.

A validated strategy is a *challenger*; promotion to *champion* is an explicit,
recorded registry action — it is NOT a deployment (Phase 2 has no execution). Only a
``validated`` version may be promoted, so a strategy that looked good in-sample but
failed out-of-sample can never become champion ("no promotion on in-sample alone").
"""
from __future__ import annotations

from sqlalchemy import select, update

from quantflo.data.db import session_scope
from quantflo.strategies.models import StrategyVersion


class ModelRegistry:
    """Champion/challenger state over ``strategy_versions`` (registry only, no deploy)."""

    def __init__(self, tenant: str = "local") -> None:
        self._tenant = tenant

    async def mark_challenger(self, version_id: int) -> None:
        """Mark a validated version as a challenger (refuses non-validated versions)."""
        async with session_scope() as session:
            version = (
                await session.execute(select(StrategyVersion).where(StrategyVersion.id == version_id))
            ).scalar_one()
            if version.status != "validated":
                raise ValueError(
                    f"cannot mark non-validated version {version_id} (status={version.status}) "
                    "as challenger - no promotion on in-sample alone"
                )
            version.champion_status = "challenger"

    async def promote_to_champion(self, version_id: int) -> None:
        """Promote a validated challenger to champion (records state; does NOT deploy)."""
        async with session_scope() as session:
            version = (
                await session.execute(select(StrategyVersion).where(StrategyVersion.id == version_id))
            ).scalar_one()
            if version.status != "validated":
                raise ValueError(
                    f"cannot promote non-validated version {version_id} (status={version.status}) "
                    "to champion - no promotion on in-sample alone"
                )
            # Demote any current champion of the same strategy key.
            await session.execute(
                update(StrategyVersion)
                .where(
                    StrategyVersion.tenant_id == self._tenant,
                    StrategyVersion.strategy_key == version.strategy_key,
                    StrategyVersion.champion_status == "champion",
                )
                .values(champion_status="challenger")
            )
            version.champion_status = "champion"

    async def current_champion(self, strategy_key: str) -> StrategyVersion | None:
        async with session_scope() as session:
            return (
                await session.execute(
                    select(StrategyVersion).where(
                        StrategyVersion.tenant_id == self._tenant,
                        StrategyVersion.strategy_key == strategy_key,
                        StrategyVersion.champion_status == "champion",
                    )
                )
            ).scalar_one_or_none()

    async def list_by_champion_status(self, champion_status: str) -> list[StrategyVersion]:
        async with session_scope() as session:
            return list(
                (
                    await session.execute(
                        select(StrategyVersion)
                        .where(
                            StrategyVersion.tenant_id == self._tenant,
                            StrategyVersion.champion_status == champion_status,
                        )
                        .order_by(StrategyVersion.strategy_key, StrategyVersion.version)
                    )
                )
                .scalars()
                .all()
            )
