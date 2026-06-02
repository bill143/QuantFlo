# Team 7 â€” Risk & Compliance Team

**Key:** `risk_compliance`  Â·  **Swarm agent:** `risk_compliance`

## Role

Pre-trade and post-trade risk limits, exposure control, and compliance.

## Responsibilities

- Enforce position, loss, and exposure limits.
- Run pre-trade risk checks before any order is routed.
- Maintain the compliance and audit trail.
- Coordinate with Governance (Team 10) on limit breaches.

## Phase 0 status

Scaffold only. This team is **registrable as a swarm agent** (see
`quantflo/orchestration/teams.py` and `scripts/boot_swarm.py`) but has **no
internal logic yet** â€” that is correct for Phase 0. Implementation lands in later
phases.

> **Role-text provenance:** the role statement above is synthesized from the
> QUANTFLO team taxonomy and is **pending reconciliation with the verbatim
> Master Project Plan** role text (tracked as a known gap in the Phase 0 gate
> report). Keys, numbers, and names are stable and are asserted by the boot
> smoke test.