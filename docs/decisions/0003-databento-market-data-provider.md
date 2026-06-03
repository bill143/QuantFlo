# ADR 0003 — Market-data provider: Databento (not Interactive Brokers) for Phase 1 ingestion

- **Status:** Accepted
- **Date:** 2026-06-03
- **Phase:** 1 (data layer & secure vault)
- **Deciders:** QUANTFLO principal architect

## Context

Phase 1 requires a vendor-abstracted ingestion layer with **one real adapter** delivering
**real historical bars** (no synthetic/mock data) for the six CME index futures
(NQ, MNQ, ES, MES, YM, MYM) across ≥2 timeframes, normalized to the `bars` schema, with
correct continuous-futures roll handling. The two realistic candidates were **Databento**
and **Interactive Brokers (IB)**.

## Decision

**Use Databento** (`databento` Python client, dataset `GLBX.MDP3`, `ohlcv-1d`/`ohlcv-1h`
schemas, raw-symbol per-contract requests) as the single real provider behind the
`MarketDataProvider` interface. IB remains a candidate for the **execution/brokerage**
layer in a later phase — that is an order-routing concern, not a historical-data concern.

## Rationale

1. **Headless, reproducible historical access.** Databento's historical API is a stateless
   HTTP service: a single API key returns deterministic, point-in-time CME data. IB's
   historical data requires a **funded account plus a running TWS / IB Gateway desktop
   process**, making CI and unattended ingestion fragile.
2. **Direct exchange-of-record data.** `GLBX.MDP3` is CME Globex MDP 3.0 — the authoritative
   venue feed for these contracts. IB historical bars are broker-aggregated and subject to
   **pacing violations** (≈ 60 requests / 10 min) that throttle multi-instrument backfills.
3. **Clean per-contract symbology.** Databento exposes raw CME symbols (`ESH4`) and
   continuous symbology (`ES.c.0`), so QUANTFLO's own roll engine can select contracts and
   stitch the series. (Probe confirmed: `ESH4` resolves, `ESH24` does not — single-digit
   year — and `to_df()` returns tz-aware UTC `ts_event` + float OHLC + integer volume.)
4. **Cost model fits a personal engine.** Pay-per-use with free starter credits; OHLCV is
   cheap. No market-data-subscription entitlements or brokerage minimums.
5. **Separation of concerns.** Coupling historical data to a brokerage (IB) would entangle
   the data layer with live-trading credentials and uptime. Keeping data (Databento) and
   future execution (IB/Tradovate/etc.) as **independent providers** is cleaner and matches
   the swappable-vendor requirement.

## Consequences

- **Positive:** real CME data ingests headlessly and in CI (the pipeline test uses a fake
  provider — no network/cost — while `scripts/ingest_data.py` runs the real backfill). The
  `MarketDataProvider` ABC means a second adapter (IB, Polygon, …) can be added without
  touching the ingestor, roll engine, or quality gates.
- **Negative / watch-items:** Databento is a paid dependency (key in `.env`, never
  committed); the real backfill is **not** run in CI (cost + secret). The committed
  evidence is the local real run (see `docs/PHASE_1_GATE.md`, gate B): 12,312 real bars.
- **Revisit when:** the execution phase needs live order routing — evaluate IB/Tradovate
  there, as an execution provider, independent of this data decision.
