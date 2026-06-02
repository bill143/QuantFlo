# Team 6 â€” Data Engineering Team

**Key:** `data_engineering`  Â·  **Swarm agent:** `data_engineering`

## Role

Market-data ingestion, normalization, storage, and feature pipelines.

## Responsibilities

- Ingest CME/CBOT market data for the six scope instruments.
- Normalize, timestamp, and quality-check incoming data.
- Maintain the storage layer and feature pipelines.
- Serve clean data to Research, Testing, and ModelOps.

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