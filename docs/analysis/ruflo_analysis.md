# Source Analysis — `ruvnet/ruflo` (orchestration backbone)

> QUANTFLO Stage 1 repo analysis. Real file paths relative to `_research/ruflo/`.
> ruflo is the **chosen orchestration backbone** (vendored as `ruflo@3.10.31` via
> npm), so this report frames capabilities as *leverage vs ignore*, not extract.

## 1. License (authoritative)

- **SPDX:** `MIT` (GitHub Licenses API; `LICENSE` = MIT, "Copyright (c) 2024-2026 ruvnet";
  `package.json` `"license": "MIT"`; npm `ruflo@3.10.31` = MIT).
- **Classification:** **PERMISSIVE.** QUANTFLO Team-5 may use, modify, and vendor
  directly; only obligation is preserving the copyright + permission notice.
- **Clean-room required?** **No.** (The *external* `neural-trader` npm package some
  plugins invoke is a separate project — verify independently; see the plugin report.)

## 2. Architecture summary (TS/npm)

ruflo is the npm alias-wrapper over `claude-flow` (published `package.json` `name` is
literally `claude-flow`, v3.10.31, ESM, Node `>=20`). The `bin` `claude-flow` →
`bin/cli.js` (12-line proxy) → `v3/@claude-flow/cli/bin/cli.js`. The real product is a
TypeScript ESM monorepo under `v3/@claude-flow/*` (cli, swarm, memory, mcp, neural,
hooks, security, …). It is a **meta-harness**: ruflo does *coordination* (swarm
topology, consensus, memory, MCP tool surface, hooks/self-learning) while actual code
execution is delegated to Claude Code's Task tool / headless `claude -p`. Heavy native
bits (`agentdb`, `@ruvector/*`, transformers) are **`optionalDependencies`**, so the
core degrades gracefully when absent. A separate Claude Code **plugin marketplace**
lives at `plugins/` (38 `ruflo-*` plugins) — markdown skills/agents + small TS adapters,
not compiled into the CLI.

| Path | Purpose |
|------|---------|
| `bin/cli.js` | umbrella entrypoint (proxy) |
| `v3/@claude-flow/cli/bin/cli.js` | **real CLI entrypoint** (26 cmds / 140+ subcmds) |
| `v3/@claude-flow/cli/bin/mcp-server.js` | **MCP server** (stdio JSON-RPC 2.0; serverInfo `"ruflo"`) |
| `v3/@claude-flow/swarm/src/unified-coordinator.ts` | **canonical spawn primitive** (`registerAgent`, `spawnAgent`, `spawnFullHierarchy`) |
| `v3/@claude-flow/swarm/src/queen-coordinator.ts` | queen/hive-mind orchestrator |
| `v3/@claude-flow/swarm/src/topology-manager.ts` | mesh/hierarchical/centralized/hybrid topology |
| `v3/@claude-flow/swarm/src/consensus/` | `raft.ts`, `byzantine.ts`, `gossip.ts` + ed25519 transport |
| `v3/@claude-flow/swarm/src/coordination/agent-registry.ts` | agent registry/lifecycle/health |
| `v3/@claude-flow/memory/src/` | `hnsw-index.ts`, `agentdb-backend.ts`, `rvf-backend.ts` |
| `v3/@claude-flow/neural/src/` | `sona-manager.ts`, `reasoning-bank.ts` (self-learning) |
| `v3/@claude-flow/hooks/src/` | hook registry/executor + background workers |

## 3. Capabilities to LEVERAGE (since MIT) → QUANTFLO team

| Capability | Path | Consumer team | Why |
|------------|------|---------------|-----|
| Unified swarm coordinator + spawn primitives | `swarm/src/unified-coordinator.ts` | Orchestration (5) | Canonical engine to coordinate the 10 team-agents. |
| Queen coordinator (hive-mind) | `swarm/src/queen-coordinator.ts` | Orchestration (5) | Queen-led task analysis + capability-scored delegation maps to "Team-5 leads 10 teams". |
| Topology manager | `swarm/src/topology-manager.ts` | Orchestration (5) | Hierarchical for tight control vs mesh for peer coordination, with failover. |
| Consensus (Raft/Byzantine/Gossip) + signed transport | `swarm/src/consensus/*` | Orchestration (5) / Governance (10) | Byzantine BFT (f<n/3) lets a money-handling system tolerate a faulty/compromised agent; ed25519 = tamper-evident votes. |
| Agent registry + lifecycle + health | `swarm/src/coordination/agent-registry.ts` | Orchestration (5) / Monitoring (9) | Register/spawn/terminate + heartbeat health for the 10 agents. |
| MCP server + tool surface | `cli/bin/mcp-server.js`, `cli/src/mcp-tools/*` | All teams | How a Python Team-5 drives ruflo (stdio MCP client) without reimplementing. |
| AgentDB / HNSW / RVF vector memory | `memory/src/hnsw-index.ts`, `agentdb-backend.ts` | ModelOps (8) / Data-eng (6) | Namespaced vector memory for market regimes/signals/trade patterns. |
| SONA self-learning + ReasoningBank | `neural/src/sona-manager.ts`, `reasoning-bank.ts` | ModelOps (8) | Learn which agent routings/strategies succeeded. |
| Hooks + background workers | `hooks/src/` | Orchestration (5) / Monitoring (9) | Pre/post task/edit/command hooks + guardrail workers. |
| Plugin marketplace pattern | `.claude-plugin/marketplace.json`, `plugins/ruflo-*` | Orchestration (5) / Data-eng (6) | Fork the packaging pattern to ship QUANTFLO's own first-party trading plugins. |

## 4. Capabilities to IGNORE for QUANTFLO
- `ruflo-neural-trader` **as a trading engine** — it is NOT one; it shells out to an
  external `npx neural-trader` npm package (see the plugin report). Leverage the
  agent/pipeline prompts + risk-gating contract only.
- Codex dual-mode (`v3/@claude-flow/codex`) — OpenAI-Codex workers; irrelevant.
- GitHub/repo-ops agents + plugins (`github-tools.ts`, `pr-manager`, `release-swarm`) — dev-workflow automation, not trading.
- IPFS/Pinata plugin-registry distribution — vendor plugins locally; don't depend on the public registry.
- Domain plugins (healthcare/legal/iot/etc.) + SPARC scaffolding — out of scope.

## 5. Integration constraints / risks (evidence)
- **Eager embedding-model download** — `v3/@claude-flow/embeddings/src/transformers-loader.ts`
  + `cli/src/memory/bge-embedder.ts` resolve `all-MiniLM-L6-v2` (384-dim) ONNX at
  runtime from HuggingFace. **Verified live:** running the ruflo CLI for `--version`
  triggered `Loading ONNX model: all-MiniLM-L6-v2...` and a HuggingFace download — so
  the CLI is **not** a safe health-probe. Mitigation: these are optional deps; the
  swarm/consensus path runs without them; pre-cache or disable embeddings for offline.
  (This is why QUANTFLO's `scripts/boot_swarm.py` probe is filesystem-only.)
- **Heavy optional native deps** — `@ruvector/router-linux-x64-gnu` is Linux-x64-only;
  Windows path is fragile (repo ships `bin/npx-repair.js`, Windows orphan-PID
  reconciliation in `swarm-tools.ts`).
- **Node ≥20 / ESM-only** — a Python Team-5 must bridge via the **stdio MCP server** or
  by shelling the CLI, not in-process FFI.
- **Version/identity churn** — published name is `claude-flow` v3.10.31 while internal
  headers say v3.6.x and sub-packages are `3.0.0-alpha.*`; large lockfiles with a long
  CVE-pinning `overrides` block. Pin exact (done: 3.10.31); re-audit on bump.
- **Overstated perf** — CLAUDE.md repeats "150x–12,500x HNSW" / "2.49x–7.47x Flash
  Attention", but the repo's own audit (`docs/reviews/intelligence-system-audit-2026-05-29.md`)
  marks HNSW ~1.9x–4.7x measured and Flash Attention **unverified**. Benchmark in
  QUANTFLO's own environment; do not trust marketing numbers.

## 6. Feasibility probe

- **Vendored-install runtime check — PARTIAL PASS:** `npm install` pinned `ruflo@3.10.31`
  (1,062 packages; `node_modules/ruflo/package.json` → `3.10.31`, MIT). The CLI boots
  (it began loading the ONNX embedding model), confirming the runtime is present — but
  the eager model download makes a clean `--version` probe unreliable, so QUANTFLO's
  boot probe reads the pinned `package.json` instead.
- **Swarm/consensus unit suites — DEFERRED (network-free, build required):** the
  capabilities to leverage are covered by in-process vitest suites under
  `v3/@claude-flow/swarm/__tests__/` (`queen-coordinator.test.ts`, `consensus.test.ts`,
  `coordinator.test.ts`, `topology.test.ts`, all transport tests) that mock deps and use
  no network. **Blocker:** they import compiled `*.js`, so a `tsc` build is required
  first. Command for later: `cd v3/@claude-flow/swarm && npm run build && npx vitest run __tests__`.

## 7. License note (MIT)

Permissive — direct use/modification/vendoring allowed; preserve the copyright +
permission notice. ruflo is the backbone, not an extraction target: QUANTFLO's
`quantflo/orchestration/` mirrors ruflo's agent-registry/task-queue/state-bus shapes in
Python and bridges to the ruflo runtime via the stdio MCP server in Phase 1 (see
`docs/decisions/0001-ruflo-integration.md`).
