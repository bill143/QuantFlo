# Team 9 â€” Monitoring Team

**Key:** `monitoring`  Â·  **Swarm agent:** `monitoring`

## Role

Observability: system health, latency, P&L, and alerting.

## Responsibilities

- Collect metrics, logs, and traces across the platform.
- Track latency, system health, and live P&L.
- Define and route alerts to on-call.
- Feed anomalies to Governance for kill-switch decisions.

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