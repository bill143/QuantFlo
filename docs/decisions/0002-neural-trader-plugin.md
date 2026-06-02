# ADR 0002 — ruflo-neural-trader plugin: do NOT install in Phase 0

- **Status:** Accepted
- **Date:** 2026-06-01
- **Phase:** 0 (foundation)
- **Deciders:** QUANTFLO principal architect

## Context

Requirement 4.3 asks us to integrate the "costrict ruflo-neural-trader plugin" per its
analysis, or — if its license or quality fails review — to **not** install it, flag it,
and recommend an alternative. Stage 1 analysis
(`docs/analysis/neural_trader_plugin_analysis.md`) established:

- The artifact we were pointed at is
  `costrict-plugins-repo/ruvnet-ruflo-ruflo-neural-trader` — an **auto-generated mirror
  ("do not edit")** of the `ruflo-neural-trader` plugin that lives inside `ruvnet/ruflo`
  (`plugins/ruflo-neural-trader/`). The "costrict" GitHub user has **0 public repos**.
- The mirror is **MIT-licensed** and tiny (~35 KB: a `.claude-plugin/` manifest, a
  `LICENSE`, and a `README.md`). It contains **no standalone engine**.
- The plugin is a **thin wrapper**: per ruflo's own agent definitions every operation
  shells out to an **external `neural-trader` npm package** (v2.7+), which ruflo's
  README documents can **fork-bomb on non-linux-x64 hosts** and must be installed with
  `--ignore-scripts` (ref ruflo issue #1974). That package is a **separate project with
  its own, independently-unverified license**.
- `neural-trader` targets **generic/crypto AI trading**, not CME index futures.

## Decision

**Do NOT install the ruflo-neural-trader plugin (or the external `neural-trader`
package) in Phase 0.** It is flagged, and a recommendation is recorded below.

## Rationale

1. **Phase 0 forbids trading logic.** The plugin's sole purpose is trading agents and
   tools; installing it would inject trading behavior into the foundation — an automatic
   gate failure under the task's own rules.
2. **Scope mismatch.** Generic/crypto AI trading ≠ QUANTFLO's CME-index-futures scope;
   it is a poor foundation dependency.
3. **Supply-chain risk (three hops).** We were pointed at a *mirror* of a *wrapper*
   around a *third external binary* that carries a documented fork-bomb hazard and an
   unverified license. That is unacceptable for a 9.8-bar foundation.
4. **No capability lost.** ruflo itself (vendored, MIT — ADR 0001) already provides the
   swarm, memory, and agent primitives QUANTFLO needs in Phase 0.

## Recommendation (the "instead")

- Treat only the plugin's **pipeline shape** as a design reference: its 4-agent flow
  `market-analyst → trading-strategist → risk-analyst → backtest-engineer` with a
  **risk-gated live path** (ruflo ADR-126) is a useful template for QUANTFLO's
  Research/ModelOps agents.
- Defer any adoption to the **Research/ModelOps phase (Teams 1 & 8)**. If adopted then:
  (a) install from the **canonical `ruvnet/ruflo` marketplace**, not the costrict
  mirror; (b) independently **license-audit** the external `neural-trader` package;
  (c) **clean-room** QUANTFLO's own CME-futures agents from the pipeline/risk-gating
  pattern — do not take a runtime dependency on the upstream binary.

## Consequences

- **Positive:** the foundation stays trading-logic-free, scope-pure, and free of a
  risky multi-hop supply chain. No Phase 0 deliverable depends on this plugin.
- **Negative:** none material — the only "loss" is a crypto-oriented tool we did not
  want as a dependency. The reusable idea (risk-gated agent pipeline) is preserved as a
  documented design reference.
