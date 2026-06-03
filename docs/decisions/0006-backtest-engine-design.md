# ADR 0006 — Event-driven backtest engine design (adapted from quanttrader, Apache-2.0)

- **Status:** Accepted
- **Date:** 2026-06-03
- **Phase:** 2 (research → create → test engine)
- **Deciders:** QUANTFLO principal architect

## Context

The Tester needs a backtest engine that is **point-in-time correct** (no look-ahead),
applies **realistic fills + commission**, accounts futures PnL with the **contract
multiplier**, and handles the **continuous-futures roll** per-contract. The reference
implementation — quanttrader's *event-driven backtest engine + no-look-ahead DataBoard* and
*simulated brokerage (fills/commission)* and *futures-multiplier Position/PnL* — is
**Apache-2.0 (permissive)** in `EXTRACTION_DECISIONS.md`, each `✅ source PASS` (local
`tests/test_strats.py`). Permissive ⇒ **adapt with attribution** (no clean-room required).

## Decision

Implement `quantflo/backtest/engine.py` as an **event-driven** backtest, **adapted from
quanttrader's permissive design with attribution recorded** in the strategy registry
(`license_provenance = permissive_attribution` / lineage on ported strategies). Key design:

- **One-bar execution lag (no look-ahead):** the position implied by bar *t-1*'s signal is
  executed at bar *t*'s OPEN. A signal can never act on the bar it was computed from. This
  composes with the bias detectors (ADR 0005) to enforce point-in-time correctness.
- **Discrete full-size positions:** signal ∈ {-1, 0, +1} × `contracts`, so transitions are
  flat↔long, flat↔short, or a flip (close + open) — no partial fills to reconcile.
- **Per-contract roll:** when the continuous series changes contract, the position is rolled
  (close the old contract at its last close, reopen the new at the next open). A
  cross-contract price gap is therefore **never booked as PnL**; the roll costs two
  commissions, matching reality.
- **Realistic fills:** adverse slippage in ticks on every fill; commission per contract per
  side. PnL uses the instrument `point_value`.
- **Outputs:** a mark-to-market equity curve, per-trade realized PnL, and the full metric
  set (ADR 0005). **Signals only — the engine never sends an order anywhere** (the Phase-2
  hard wall).

## Verification (hand-computed, exact)

`tests/test_backtest.py`: buy&hold +3 with no costs; commission charged both sides;
roll forces 2 trades / 4 commissions / **no gap profit**; flat signal = no trades. The
validation battery (ADR/registry) runs this engine on the **real 12,312 Phase-1 bars**.

## Consequences

- **Positive:** deterministic, hand-verifiable accounting; correct futures roll; no
  look-ahead; permissive provenance (attribution, no copyleft).
- **Negative / scope:** intrabar fills are modeled at the open (no intrabar stop/trailing
  fill realism yet — freqtrade's "backtest fill-realism" ideas are a later clean-room
  refinement); positions are single-instrument and full-size.
