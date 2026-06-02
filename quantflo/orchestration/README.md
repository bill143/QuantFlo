# Team 5 â€” Orchestration Team

**Key:** `orchestration`  Â·  **Swarm agent:** `orchestration`

## Role

ruflo swarm conductor: coordinates all teams, task routing, and lifecycle.

## Responsibilities

- Own the agent registry and lifecycle (REGISTERED -> READY -> ...).
- Provide the task queue and inter-team state bus.
- Sequence and schedule cross-team workflows via ruflo.
- Expose a runnable boot entrypoint (scripts/boot_swarm.py).

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