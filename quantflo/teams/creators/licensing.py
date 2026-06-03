"""License classification + clean-room / attribution compliance decisions.

Permissive sources are adapted WITH attribution; copyleft (GPL/LGPL), network-copyleft
(AGPL), and no/unknown-license sources require a CLEAN-ROOM reimplementation (reimplement
the described behavior from public definitions; never copy source code). This module
never copies anything — it decides how a source may be used.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LicenseClass(StrEnum):
    PERMISSIVE = "permissive"
    COPYLEFT = "copyleft"
    NETWORK_COPYLEFT = "network_copyleft"
    UNKNOWN = "unknown"


_PERMISSIVE: frozenset[str] = frozenset(
    {
        "MIT", "APACHE-2.0", "APACHE", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "BSD",
        "ISC", "UNLICENSE", "0BSD", "ZLIB", "BSL-1.0",
    }
)


def classify_license(spdx: str | None) -> LicenseClass:
    if not spdx:
        return LicenseClass.UNKNOWN
    token = spdx.strip().upper()
    if token in ("NOASSERTION", "UNKNOWN", "NONE", "OTHER"):
        return LicenseClass.UNKNOWN
    if "AGPL" in token:
        return LicenseClass.NETWORK_COPYLEFT
    if "GPL" in token:  # GPL / LGPL
        return LicenseClass.COPYLEFT
    if token in _PERMISSIVE:
        return LicenseClass.PERMISSIVE
    return LicenseClass.UNKNOWN


@dataclass(frozen=True)
class ComplianceDecision:
    """How a source may be used (never a code copy for non-permissive sources)."""

    license_class: LicenseClass
    provenance: str  # permissive_attribution | clean_room
    requires_clean_room: bool
    attribution: str | None
    clean_room_note: str | None


_CLEAN_ROOM_REASON: dict[LicenseClass, str] = {
    LicenseClass.COPYLEFT: "GPL/LGPL copyleft",
    LicenseClass.NETWORK_COPYLEFT: "AGPL network-copyleft",
    LicenseClass.UNKNOWN: "no/unknown license (treated as all-rights-reserved)",
}


def compliance_decision(source_title: str, source_url: str, spdx: str | None) -> ComplianceDecision:
    """Decide attribution (permissive) vs clean-room (copyleft / AGPL / unknown)."""
    license_class = classify_license(spdx)
    if license_class == LicenseClass.PERMISSIVE:
        return ComplianceDecision(
            license_class=license_class,
            provenance="permissive_attribution",
            requires_clean_room=False,
            attribution=f"Adapted from {source_title} ({source_url}), licensed {spdx}.",
            clean_room_note=None,
        )
    reason = _CLEAN_ROOM_REASON[license_class]
    note = (
        f"CLEAN-ROOM required: {source_title} ({source_url}) is {reason}. "
        "Reimplement the described behavior from public technical-analysis definitions; "
        "DO NOT copy source code."
    )
    return ComplianceDecision(
        license_class=license_class,
        provenance="clean_room",
        requires_clean_room=True,
        attribution=None,
        clean_room_note=note,
    )
