# Team 3 â€” Testing & Validation Team

**Key:** `testers`  Â·  **Swarm agent:** `testers`

## Role

Backtest, walk-forward, and statistically validate candidate strategies.

## Responsibilities

- Run out-of-sample and walk-forward backtests on real data.
- Apply statistical-significance and overfitting checks.
- Produce performance attribution and risk diagnostics.
- Gatekeeper: only validated strategies may be promoted to Trading.

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