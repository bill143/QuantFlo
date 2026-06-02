# Team 8 â€” ModelOps Team

**Key:** `modelops`  Â·  **Swarm agent:** `modelops`

## Role

Continuous learning: model training, evaluation, deployment, and drift monitoring.

## Responsibilities

- Operate training and evaluation pipelines.
- Maintain the model registry and deployment process.
- Detect data/concept drift and trigger retraining.
- Promote models only after offline + online validation.

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