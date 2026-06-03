# ADR 0005 — Clean-room bias detectors + performance metrics (freqtrade is GPL-3.0)

- **Status:** Accepted
- **Date:** 2026-06-03
- **Phase:** 2 (research → create → test engine)
- **Deciders:** QUANTFLO principal architect

## Context

The Tester (Team 3) needs (a) **bias detectors** that catch look-ahead and recursive-
formula leakage and (b) a **performance-metrics** library (Sharpe / Sortino / Calmar /
max-drawdown / profit-factor). The reference implementations of all three are in
**freqtrade**, which is **GPL-3.0** — `docs/analysis/EXTRACTION_DECISIONS.md` marks these
features **ELITE / clean-room MANDATORY**, each carrying a green source-probe
**`✅ PASS @ 9eededca`** (probe.yml run 26902471654). QUANTFLO is proprietary, so copying
or linking GPL-3.0 code is not permitted.

## Decision

**Clean-room reimplement the observable behavior** of freqtrade's lookahead-analysis,
recursive-analysis, and performance-metrics from public definitions. **No freqtrade source
was read or copied.** Metrics are validated against the **standard quantitative (empyrical)
definitions**, not against freqtrade output.

### Behavior reproduced (the "what")

- **Lookahead-bias detector** — a strategy's PAST signals must not change when FUTURE bars
  are removed. We compute signals on the full series and on a series truncated by *cutoff*
  bars and compare the common prefix; any difference ⇒ the strategy peeked forward.
- **Recursive-formula bias detector** — a strategy's recent signals must not depend on how
  many startup bars precede them. We compute the tail signals using a short vs long startup
  window ending on the same final bars; a difference ⇒ a non-converged (recursively
  unstable) indicator.
- **Performance metrics** — Sharpe/Sortino/Calmar/max-drawdown/profit-factor/win-rate per
  the standard closed forms.

Both detectors operate at the **signal level** on the `Strategy` interface, so they apply to
any candidate. Implementation is original (`quantflo/backtest/bias.py`, `.../metrics.py`).

## Verification (behavior, not source)

- Lookahead: a planted `close.shift(-1)` strategy is **FLAGGED**; the clean EMA crossover
  passes. Recursive: a non-converged EMA(300) with a 20-bar startup is **FLAGGED**; a
  converged SMA passes. Metrics: Sharpe / max-drawdown / profit-factor asserted within
  `1e-9` of their **closed forms** (`tests/test_metrics.py`, `tests/test_bias.py`).

## Consequences

- **Positive:** QUANTFLO gets the rigor toolkit with **no GPL exposure**; metrics are
  validated against the math, not a copied implementation.
- **Negative / scope:** the detectors are signal-level (not column-level like freqtrade's),
  which is sufficient for a signal-emitting strategy framework but does not localize *which*
  indicator leaks. A column-level analysis is a possible later refinement.
- **License note:** reproducing public, factual definitions with original code carries **no**
  GPL obligation.
