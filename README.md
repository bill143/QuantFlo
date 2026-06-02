# QUANTFLO

**Autonomous, swarm-orchestrated trading platform for CME index futures.**

QUANTFLO is a multi-agent system that researches, builds, validates, and (in
later phases) trades a fixed universe of CME/CBOT equity-index futures. It is
organized as ten cooperating **teams**, each exposed as a swarm agent and
coordinated by the [ruflo](https://github.com/ruvnet/ruflo) orchestration
backbone.

> **Phase 0 (this branch) delivers the foundation only:** structure, ruflo
> integration, and documented decisions. There is **no** strategy, indicator,
> backtest, risk, broker, or execution logic yet — that is intentional and
> correct for the foundation phase.

## Scope instruments

CME/CBOT index futures only:

| Symbol | Contract | Exchange | Tick | Point value | Tick value |
|--------|----------|----------|------|-------------|------------|
| NQ  | E-mini Nasdaq-100      | CME  | 0.25 | $20    | $5.00  |
| MNQ | Micro E-mini Nasdaq-100| CME  | 0.25 | $2     | $0.50  |
| ES  | E-mini S&P 500         | CME  | 0.25 | $50    | $12.50 |
| MES | Micro E-mini S&P 500   | CME  | 0.25 | $5     | $1.25  |
| YM  | E-mini Dow             | CBOT | 1.00 | $5     | $5.00  |
| MYM | Micro E-mini Dow       | CBOT | 1.00 | $0.50  | $0.50  |

Authoritative definitions live in `quantflo/core/instruments/instruments.py`.

## The ten teams

| # | Team | Package | Role (synthesized — see note) |
|---|------|---------|------|
| 1 | Research | `quantflo/teams/researchers` | Market research, hypothesis generation, signal discovery |
| 2 | Strategy Creation | `quantflo/teams/creators` | Translate research into candidate strategy specs |
| 3 | Testing & Validation | `quantflo/teams/testers` | Backtest, walk-forward, statistical validation |
| 4 | Trading | `quantflo/teams/traders` | Order routing & lifecycle (within risk limits) |
| 5 | Orchestration | `quantflo/orchestration` | ruflo swarm conductor; task routing & lifecycle |
| 6 | Data Engineering | `quantflo/teams/data_engineering` | Ingestion, normalization, storage, features |
| 7 | Risk & Compliance | `quantflo/teams/risk_compliance` | Pre/post-trade limits, exposure, compliance |
| 8 | ModelOps | `quantflo/teams/modelops` | Continuous learning: train, eval, deploy, drift |
| 9 | Monitoring | `quantflo/teams/monitoring` | Observability: health, latency, P&L, alerting |
| 10 | Governance | `quantflo/teams/governance` | Kill-switch authority, change control, go/no-go |

> **Note on role text:** the role statements are synthesized from the QUANTFLO
> team taxonomy and are **pending reconciliation with the verbatim Master Project
> Plan**. This is tracked as a known gap in the Phase 0 gate report. Team keys,
> numbers, and names are stable and asserted by the boot smoke test.

## Repository layout

```
quantflo/
  orchestration/      Team 5 — ruflo swarm conductor (agent registry, task queue, lifecycle)
  teams/              Teams 1-4, 6-10 — scaffold packages (no internal logic in Phase 0)
  core/
    config/           Typed settings surface (pydantic-settings)
    schemas/          Shared data schemas (scaffold)
    state_bus/        Inter-team state bus (interface + in-memory impl)
    instruments/      NQ MNQ ES MES YM MYM contract definitions
  data/               Data layer scaffold (no ingestion yet)
  execution/          Broker-driver scaffold (empty)
  strategies/         Strategy registry scaffold (empty)
  dashboard/          Next.js operator dashboard (placeholder)
docs/
  analysis/           Stage 1 source-repo analyses + EXTRACTION_DECISIONS.md
  architecture/       Architecture notes
  decisions/          ADRs
tests/                Pytest suite (smoke + config/data tests)
infra/docker/         Container scaffold
scripts/              boot_swarm.py entrypoint
.github/workflows/    CI (ruff · mypy · pytest)
```

## Quickstart

```powershell
# 1. Create + activate a virtual environment (Python 3.11+)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install the package + dev tooling
pip install -e ".[dev]"

# 3. Boot the swarm (registers all 10 teams, prints roles, exits cleanly)
python scripts/boot_swarm.py

# 4. Run the quality gate locally
ruff check .
mypy
pytest --cov=quantflo --cov-report=term-missing
```

## Orchestration backbone

ruflo is the orchestration backbone, vendored as a **pinned npm dependency**
(`ruflo@3.10.31`) — see [`docs/decisions/0001-ruflo-integration.md`](docs/decisions/0001-ruflo-integration.md).
The Python layer in `quantflo/orchestration/` provides the agent registry, task
queue, and state-bus contract that bridges to the ruflo runtime in Phase 1. The
`ruflo-neural-trader` plugin decision is recorded in
[`docs/decisions/0002-neural-trader-plugin.md`](docs/decisions/0002-neural-trader-plugin.md).

## Phased plan

| Phase | Focus |
|-------|-------|
| **0 — Foundation** (this branch) | Architecture analysis, scaffold, ruflo integration, extraction decisions. No trading logic. |
| 1 — Data & Vault | Market-data ingestion (Team 6), secrets/vault, state bus over Redis. |
| 2 — Research & Strategy | Research signals (Team 1) and strategy specs (Team 2). |
| 3 — Testing & Validation | Backtest/walk-forward engine (Team 3), OOS validation. |
| 4 — Risk & Execution | Risk limits (Team 7), broker drivers & order lifecycle (Team 4), sim-first. |
| 5 — ModelOps & Monitoring | Continuous learning (Team 8), observability (Team 9). |
| 6 — Governance & Go-Live | Kill-switch, change control, go/no-go (Team 10). |

Each later phase ports features only as authorized by
[`docs/analysis/EXTRACTION_DECISIONS.md`](docs/analysis/EXTRACTION_DECISIONS.md).

## License

Proprietary — © QUANTFLO. Third-party source repositories analyzed in Stage 1
retain their own licenses; see `docs/analysis/` for per-repo classification and
clean-room requirements.
