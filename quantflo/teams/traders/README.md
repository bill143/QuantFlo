# Team 4 â€” Trading Team

**Key:** `traders`  Â·  **Swarm agent:** `traders`

## Role

Route validated strategies to execution and manage the order lifecycle.

## Responsibilities

- Route orders and manage fills, positions, and the order lifecycle.
- Operate broker drivers (added in a later phase).
- Trade strictly within Risk & Compliance (Team 7) limits.
- Report execution quality to Monitoring (Team 9).

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