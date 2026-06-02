# ADR 0001 — ruflo orchestration backbone integration

- **Status:** Accepted
- **Date:** 2026-06-01
- **Phase:** 0 (foundation)
- **Deciders:** QUANTFLO principal architect

## Context

QUANTFLO needs a multi-agent orchestration backbone to coordinate its ten team
agents (Team 5). The mandated backbone is `ruvnet/ruflo`. Stage 1 analysis
(`docs/analysis/ruflo_analysis.md`) established the relevant facts:

- ruflo is **MIT-licensed** (permissive) — verified via GitHub API, the `LICENSE`
  file, and npm.
- ruflo is a **TypeScript / npm** project, not a Python library. It is published to
  npm as `ruflo@3.10.31` (the package `name` internally is `claude-flow`). The git
  repository is ~526 MB; the npm package unpacks to ~10 MB.
- It requires **Node ≥ 20**, is **ESM-only**, and several heavy components
  (`agentdb`, `@ruvector/*`, transformers) are `optionalDependencies`.
- The CLI **eagerly loads/downloads an `all-MiniLM-L6-v2` ONNX embedding model on
  startup** (verified live during this phase), so executing the CLI has network
  side-effects and is unsuitable as a lightweight health probe.
- QUANTFLO's runnable entrypoint must be **Python** (`scripts/boot_swarm.py`), and CI
  must pass without a Node toolchain.

Two questions had to be decided: (1) **how to vendor ruflo**, and (2) **how the
Python side relates to the TypeScript runtime**.

## Decision

### 1. Vendor ruflo as a pinned npm dependency (not a git submodule)

`package.json` pins `"ruflo": "3.10.31"` (exact), and `npm install` generated a
committed `package-lock.json`. `node_modules/` is gitignored.

**Why pinned npm install over a git submodule:**

- ruflo is an npm-published artifact we **consume, not modify** — a submodule would
  vendor 526 MB of source we never edit.
- A pinned version + committed lockfile gives **reproducible, hash-verified** installs
  and a clean upgrade/audit path (ruflo ships a long CVE-pinning `overrides` block).
- npm is already required for the dashboard (Next.js), so no new toolchain is added.

### 2. Python orchestration skeleton mirrors ruflo's shapes; bridge via MCP in Phase 1

`quantflo/orchestration/` implements, in pure Python, the same primitives ruflo
exposes — an **agent registry + lifecycle** (`agent.py`), a **task queue**
(`task_queue.py`), and an **inter-team state-bus contract** (`quantflo/core/state_bus/`,
interface + in-memory impl). `SwarmConductor` registers all ten teams as agents and
runs a boot lifecycle. This keeps `scripts/boot_swarm.py` runnable in pure Python and
CI green without Node.

The **live bridge** from this Python layer to the ruflo runtime is deferred to Phase 1
and will use ruflo's **stdio MCP server** (`v3/@claude-flow/cli/bin/mcp-server.js`,
JSON-RPC 2.0) — i.e. Python Team-5 spawns an MCP client to ruflo, rather than any
in-process FFI (impossible across Python↔Node ESM). The `ruflo_enabled` setting and
the filesystem-only `probe_ruflo()` in `boot_swarm.py` are the seams for this.

## Consequences

**Positive**
- Reproducible, license-clean (MIT) backbone with an exact pin and lockfile.
- Phase 0 boot + CI run with zero Node dependency; Node is only needed when the Phase 1
  MCP bridge is activated.
- The Python abstractions are testable today (98% covered) and define the contract the
  ruflo bridge must satisfy.

**Negative / risks (tracked)**
- ruflo's eager embedding-model download and Linux-x64-only native optional deps
  (`@ruvector/router-linux-x64-gnu`) make the Windows/offline runtime path fragile —
  Phase 1 must pre-cache the model or disable embeddings for the control path.
- Version/identity churn (published `claude-flow` v3.10.31 vs internal v3.6.x headers);
  re-audit the pin on every bump.
- Some ruflo perf claims are overstated vs its own audit; QUANTFLO will benchmark
  independently before relying on AgentDB/HNSW or SONA.

## Alternatives considered

- **Git submodule of ruflo** — rejected: vendors 526 MB of unmodified source, heavier
  to update/audit than a pinned npm artifact.
- **Reimplement orchestration natively in Python, drop ruflo** — rejected: ruflo is
  mandated and provides mature swarm/consensus/memory primitives (MIT) we should
  leverage, not rebuild.
- **In-process Python↔Node FFI** — rejected: ruflo is ESM-only Node ≥20; the supported,
  clean integration surface is the stdio MCP server.
