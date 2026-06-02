# Source Analysis — `costrict` ruflo-neural-trader plugin

> QUANTFLO Stage 1 repo analysis. The plugin governs the Stage 3 install decision
> (requirement 4.3). Canonical source: the `ruflo-neural-trader` plugin inside
> `ruvnet/ruflo` (`plugins/ruflo-neural-trader/`), mirrored at
> `costrict-plugins-repo/ruvnet-ruflo-ruflo-neural-trader` (the "costrict" handle).

## 1. License (authoritative)

- **Mirror repo SPDX:** `MIT` (GitHub Licenses API; `LICENSE` = MIT, "Copyright (c)
  2024-2026 ruvnet"). The in-ruflo plugin (`plugins/ruflo-neural-trader/.claude-plugin/plugin.json`)
  also declares MIT.
- **Classification:** **PERMISSIVE (MIT).**
- **Important:** the plugin is only a thin wrapper. The actual engine is the **external
  `neural-trader` npm package** (`npmjs.com/package/neural-trader`), a **separate
  project with its own license** that must be verified independently before any
  dependency is taken.

## 2. What it actually is

- The **mirror repo** (`_research/neural-trader-plugin/`) contains only three items:
  `.claude-plugin/` (manifest), `LICENSE`, `README.md`. ~35 KB, language "Shell". It is
  an **auto-generated mirror** ("do not edit") — i.e. a republished copy, not the source
  of truth. The "costrict" GitHub user has **0 public repos**.
- The plugin is one of ruflo's 38 marketplace plugins. Per ruflo's README it provides
  "AI trading with 4 agents, backtesting, 112+ tools" and is installed via
  `/plugin install ruflo-neural-trader@ruflo`.
- Per ruflo's own agent definitions (`plugins/ruflo-neural-trader/agents/trading-strategist.md`),
  every operation **shells out to the external `npx neural-trader` package** (v2.7+).
  ruflo's README warns that package can fork-bomb on non-linux-x64 hosts and must be
  installed with `--ignore-scripts` (ref issue #1974).

## 3. Elite verdict for QUANTFLO

| Aspect | Verdict | Reason |
|--------|---------|--------|
| The plugin wrapper (manifest + agent prompts + risk-gated pipeline) | **ELITE (pattern only)** | The 4-agent pipeline `market-analyst → trading-strategist → risk-analyst → backtest-engineer` with a **risk-gated live path** (ruflo ADR-126) is a good *template* for QUANTFLO's modelops/research agent design. |
| The underlying `neural-trader` npm engine | **NOT-ELITE / REJECT as a dependency** | Generic/crypto AI-trading tool, not CME-futures focused; opaque 112-tool surface; fork-bomb/`--ignore-scripts` warning = supply-chain risk; separate unverified license. |

## 4. Install decision (requirement 4.3) — **DO NOT INSTALL in Phase 0**

Recorded in full in `docs/decisions/0002-neural-trader-plugin.md`. Summary rationale:

1. **Phase 0 forbids trading logic.** The plugin's entire purpose is trading agents +
   tools; installing it injects trading behavior into the foundation — an automatic
   gate failure by the task's own rules.
2. **Scope mismatch.** `neural-trader` targets generic/crypto AI trading; QUANTFLO is
   CME index futures only. It is not a good foundation dependency.
3. **Supply-chain risk.** The canonical artifact we were pointed at is a costrict
   **auto-generated mirror** ("do not edit") of a ruvnet plugin, and the real engine is
   a third external npm package with a documented fork-bomb/`--ignore-scripts` hazard
   and an independently-unverified license. Vendoring a mirror of a wrapper around a
   risky binary is three supply-chain hops too many for a 9.8-bar foundation.
4. **No loss of capability.** ruflo itself (already vendored, MIT) provides the swarm,
   memory, and agent primitives QUANTFLO needs. Nothing in Phase 0 depends on this plugin.

**Recommendation:** defer evaluation to the Research/ModelOps phase (Teams 1 & 8). If
adopted later, (a) install from the **canonical `ruvnet/ruflo` marketplace**, not the
costrict mirror; (b) independently license-audit the external `neural-trader` package;
(c) clean-room QUANTFLO's own CME-futures agents using only the plugin's *pipeline
shape and risk-gating contract* as a design reference — do not depend on the upstream
binary.

## 5. Feasibility probe

**Not applicable / not run.** The plugin is a manifest wrapper with no standalone
runnable feature in the mirror repo; the engine it invokes is an external package that
is explicitly **rejected as a dependency** (above). Per the rule "we don't extract
broken features," nothing here is marked ELITE-for-extraction beyond the *pipeline
pattern*, whose verification is a later-phase design review, not a code probe.
