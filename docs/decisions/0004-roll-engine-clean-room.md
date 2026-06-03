# ADR 0004 — Continuous-futures roll engine: clean-room reimplementation (lumibot is GPL-3.0)

- **Status:** Accepted
- **Date:** 2026-06-03
- **Phase:** 1 (data layer & secure vault)
- **Deciders:** QUANTFLO principal architect

## Context

Continuous-futures construction needs a roll engine: index futures expire quarterly, so a
gap-free price series must switch ("roll") from the front contract to the next near expiry.
**Lumibot** (`Lumiwealth/lumibot`) ships such an engine, but lumibot is **GPL-3.0**
(see the Phase-0 license audit, `docs/analysis/lumibot_analysis.md`, which flagged the
MIT/GPL conflict). QUANTFLO is a **proprietary** codebase: copying or linking GPL-3.0 code
would impose copyleft on the whole project and is not permitted. The Phase-1 mandate is
therefore explicit: **clean-room reimplement the roll behavior — reimplement, do not copy —
and cite the behavior (not the code) here.**

## Decision

Implement `quantflo/data/roll.py` **independently from public CME contract conventions**,
matching only the **observable behavioral contract** of a quarterly index-futures
continuous series. **No lumibot source was read, ported, or copied during implementation.**

### Behavioral contract reproduced (the "what", from public CME conventions)

- **Cycle:** the quarterly March / June / September / December cycle, CME month codes
  **H / M / U / Z**.
- **Expiry:** the **third Friday** of the contract month (standard CME equity-index expiry).
- **Roll point:** roll from the front contract to the next a fixed number of **exchange
  trading days before expiry** — QUANTFLO uses **8 CME trading days** (a common index
  continuous-contract convention; configurable via `offset_bdays`).
- **Calendar:** exchange holidays/half-days come from the maintained, permissively-licensed
  `pandas_market_calendars` CME equity calendar — **not** from any lumibot data.

### Implementation (the "how", original)

Pure calendar arithmetic: `third_friday()` (first-Friday + 14 days), `roll_date()` (the
Nth valid CME trading day before expiry), `active_contract[_parts]()` (first quarter whose
roll date is still in the future), `roll_schedule()` (segment boundaries), and
`databento_raw_symbol()` (CME single-digit-year mapping). None of these mirror lumibot's
internal structure; they derive from CME specs and the calendar library.

## Verification (behavior, not source, is what we match)

- Third Fridays exact: 2024 H/M/U/Z = 2024-03-15 / 06-21 / 09-20 / 12-20; 2023-12 = 12-15.
- Roll date: 8 CME trading days before 2024-03-15 → **2024-03-05**.
- 2024 ES schedule: `ESH24 → ESM24 (Mar 5) → ESU24 (Jun 11) → ESZ24 (Sep 10) → ESH25 (Dec 10)`.
- **Confirmed on real Databento data** (gate B): every instrument's `bars.contract` switches
  `…H24 → …M24` exactly at **2024-03-05** (ES 1h: `ESH24` ends `2024-03-04 23:00Z`,
  `ESM24` starts `2024-03-05 00:00Z`).

Unit tests in `tests/test_roll.py` assert these against known dates.

## Consequences

- **Positive:** QUANTFLO gets correct continuous-futures roll handling with **no GPL
  exposure** — the proprietary license stays intact. The offset and cycle are parameters,
  so other roll conventions (e.g. volume/OI-triggered) can be layered later.
- **Negative:** the fixed-offset (8-day) rule is a calendar heuristic, not a
  liquidity-driven roll; a volume/open-interest-aware roll is a possible future refinement.
- **License note:** because we reproduced only public, factual market conventions and wrote
  original code, this is a clean-room reimplementation and carries **no** GPL obligation.
