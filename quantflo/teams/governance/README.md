# Team 10 â€” Governance Team

**Key:** `governance`  Â·  **Swarm agent:** `governance`

## Role

Kill-switch authority, change control, and final go/no-go gates.

## Responsibilities

- Own the global kill-switch and emergency-stop authority.
- Run change control and approval gates for deployments.
- Make final go/no-go decisions for live trading.
- Hold ultimate authority over platform state.

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