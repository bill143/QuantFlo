"""Team 2 (Creators): turn a scored candidate into a created, provenance-tracked strategy.

Runs license compliance (permissive -> attribution; copyleft/AGPL/unknown -> clean-room
spec, never a copy), maps the candidate to an implementable framework strategy template,
and writes a ``strategy_versions`` row (status ``created``) ready for the Tester. A
candidate with no mappable template is rejected with a recorded reason — not forced.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update

from quantflo.data.db import session_scope
from quantflo.strategies.models import ResearchCandidate, StrategyVersion
from quantflo.teams.creators.licensing import ComplianceDecision, compliance_decision

# Keyword groups -> implementable strategy template (must exist in the Tester registry).
_TEMPLATE_RULES: list[tuple[tuple[str, ...], str]] = [
    (("crossover", "ema", "moving average", "trend", "momentum", "sma", "macd"), "ema_crossover"),
]


def map_to_template(title: str, description: str | None) -> str | None:
    text = f"{title} {description or ''}".lower()
    for keywords, template_key in _TEMPLATE_RULES:
        if any(keyword in text for keyword in keywords):
            return template_key
    return None


@dataclass(frozen=True)
class CreateOutcome:
    status: str  # created | rejected
    candidate_id: int
    version_id: int | None
    reason: str
    license_class: str
    provenance: str | None


class Creator:
    """Create framework strategy versions from candidates, with license compliance."""

    def __init__(self, tenant: str = "local") -> None:
        self._tenant = tenant

    async def create_from_candidate(self, candidate_id: int) -> CreateOutcome:
        async with session_scope() as session:
            candidate = (
                await session.execute(
                    select(ResearchCandidate).where(ResearchCandidate.id == candidate_id)
                )
            ).scalar_one()
            title, url, license_spdx, description = (
                candidate.title, candidate.source_url, candidate.license, candidate.description
            )

        decision = compliance_decision(title, url, license_spdx)
        template_key = map_to_template(title, description)

        if template_key is None:
            reason = "no clean-room-implementable strategy template matches this candidate"
            await self._reject_candidate(candidate_id, reason)
            return CreateOutcome(
                status="rejected", candidate_id=candidate_id, version_id=None,
                reason=reason, license_class=str(decision.license_class), provenance=None,
            )

        version_id = await self._create_version(
            candidate_id, title, url, license_spdx, template_key, decision
        )
        return CreateOutcome(
            status="created", candidate_id=candidate_id, version_id=version_id,
            reason=f"created '{template_key}' ({decision.provenance})",
            license_class=str(decision.license_class), provenance=decision.provenance,
        )

    async def _next_version(self, strategy_key: str) -> int:
        async with session_scope() as session:
            current_max = (
                await session.execute(
                    select(func.max(StrategyVersion.version)).where(
                        StrategyVersion.tenant_id == self._tenant,
                        StrategyVersion.strategy_key == strategy_key,
                    )
                )
            ).scalar_one()
        return int(current_max or 0) + 1

    async def _create_version(
        self,
        candidate_id: int,
        title: str,
        url: str,
        license_spdx: str | None,
        template_key: str,
        decision: ComplianceDecision,
    ) -> int:
        version = await self._next_version(template_key)
        async with session_scope() as session:
            strategy_version = StrategyVersion(
                tenant_id=self._tenant,
                strategy_key=template_key,
                version=version,
                name=f"{template_key} from {title}"[:256],
                candidate_id=candidate_id,
                source_lineage=f"discovered: {url}",
                license=license_spdx,
                license_provenance=decision.provenance,
                attribution=decision.attribution,
                clean_room_spec=decision.clean_room_note,
                status="created",
            )
            session.add(strategy_version)
            await session.flush()
            new_id = strategy_version.id
            await session.execute(
                update(ResearchCandidate)
                .where(ResearchCandidate.id == candidate_id)
                .values(status="created")
            )
        return new_id

    async def _reject_candidate(self, candidate_id: int, reason: str) -> None:
        async with session_scope() as session:
            await session.execute(
                update(ResearchCandidate)
                .where(ResearchCandidate.id == candidate_id)
                .values(status="rejected")
            )
