"""Creator tests: license classification + clean-room (copyleft) vs attribution (permissive)."""
from __future__ import annotations

from sqlalchemy import delete, select

from quantflo.data.db import session_scope
from quantflo.strategies.models import ResearchCandidate, StrategyVersion
from quantflo.teams.creators import (
    Creator,
    LicenseClass,
    classify_license,
    compliance_decision,
    map_to_template,
)
from tests.conftest import requires_db

_T = "pytest"


def test_classify_license() -> None:
    assert classify_license("MIT") == LicenseClass.PERMISSIVE
    assert classify_license("Apache-2.0") == LicenseClass.PERMISSIVE
    assert classify_license("GPL-3.0") == LicenseClass.COPYLEFT
    assert classify_license("LGPL-3.0") == LicenseClass.COPYLEFT
    assert classify_license("AGPL-3.0") == LicenseClass.NETWORK_COPYLEFT
    assert classify_license(None) == LicenseClass.UNKNOWN
    assert classify_license("NOASSERTION") == LicenseClass.UNKNOWN


def test_compliance_copyleft_requires_cleanroom() -> None:
    decision = compliance_decision("a/b", "https://github.com/a/b", "GPL-3.0")
    assert decision.requires_clean_room
    assert decision.provenance == "clean_room"
    assert decision.attribution is None
    assert decision.clean_room_note and "DO NOT copy" in decision.clean_room_note


def test_compliance_permissive_attribution() -> None:
    decision = compliance_decision("a/b", "https://github.com/a/b", "MIT")
    assert not decision.requires_clean_room
    assert decision.provenance == "permissive_attribution"
    assert decision.attribution and "Adapted from a/b" in decision.attribution


def test_map_to_template() -> None:
    assert map_to_template("momentum crossover strategy", None) == "ema_crossover"
    assert map_to_template("deep learning image classifier", None) is None


async def _purge() -> None:
    async with session_scope() as session:
        await session.execute(delete(StrategyVersion).where(StrategyVersion.tenant_id == _T))
        await session.execute(delete(ResearchCandidate).where(ResearchCandidate.tenant_id == _T))


async def _candidate(title: str, license_spdx: str | None, description: str) -> int:
    async with session_scope() as session:
        candidate = ResearchCandidate(
            tenant_id=_T, source_type="github", source_url=f"https://github.com/x/{title[:16]}",
            title=title, description=description, license=license_spdx,
            dedup_hash=title[:48], status="new",
        )
        session.add(candidate)
        await session.flush()
        return candidate.id


@requires_db
async def test_creator_copyleft_produces_cleanroom_spec(pools: None) -> None:
    await _purge()
    cid = await _candidate("gpl-momentum-crossover", "GPL-3.0", "a momentum crossover trading strategy")
    outcome = await Creator(_T).create_from_candidate(cid)
    assert outcome.status == "created" and outcome.provenance == "clean_room"
    async with session_scope() as session:
        version = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.candidate_id == cid))
        ).scalar_one()
        assert version.license_provenance == "clean_room"
        assert version.attribution is None
        assert version.clean_room_spec and "DO NOT copy" in version.clean_room_spec
        assert version.status == "created" and version.strategy_key == "ema_crossover"
        candidate = (
            await session.execute(select(ResearchCandidate).where(ResearchCandidate.id == cid))
        ).scalar_one()
        assert candidate.status == "created"
    await _purge()


@requires_db
async def test_creator_permissive_records_attribution(pools: None) -> None:
    await _purge()
    cid = await _candidate("mit-ema-trend", "MIT", "EMA trend following strategy")
    outcome = await Creator(_T).create_from_candidate(cid)
    assert outcome.status == "created" and outcome.provenance == "permissive_attribution"
    async with session_scope() as session:
        version = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.candidate_id == cid))
        ).scalar_one()
        assert version.license_provenance == "permissive_attribution"
        assert version.attribution and "Adapted from" in version.attribution
        assert version.clean_room_spec is None
    await _purge()


@requires_db
async def test_creator_rejects_unmappable(pools: None) -> None:
    await _purge()
    cid = await _candidate("dl-image-classifier", "MIT", "a deep learning image classifier")
    outcome = await Creator(_T).create_from_candidate(cid)
    assert outcome.status == "rejected"
    async with session_scope() as session:
        candidate = (
            await session.execute(select(ResearchCandidate).where(ResearchCandidate.id == cid))
        ).scalar_one()
        assert candidate.status == "rejected"
        versions = (
            await session.execute(select(StrategyVersion).where(StrategyVersion.tenant_id == _T))
        ).scalars().all()
        assert versions == []
    await _purge()
