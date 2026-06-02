# Source Analysis — `day0market/pyalgotrader`

> QUANTFLO Stage 1 repo analysis. Real file paths relative to
> `_research/pyalgotrader/`. QUANTFLO scope: CME index futures (NQ MNQ ES MES YM MYM).

## 1. License (authoritative)

- **GitHub API:** `NOASSERTION` ("Other") — auto-classifier could not match.
- **Actual `LICENSE` file (read directly):** **MIT License** — "Original work
  Copyright (c) 2015-present, Xiaoyou Chen" (vnpy author) + "Modified work
  Copyright 2019-present Alex Hurko". The repo is a **vn.py (`vnpy`) derivative**.
- **Classification:** **PERMISSIVE (MIT).** The GitHub "Other" label is a
  false-negative caused by the dual-copyright preamble.
- **Clean-room required?** **No.** Direct reuse allowed; retain the MIT notice and
  credit **both** vnpy (Xiaoyou Chen) and the pyalgotrader fork (Alex Hurko).

## 2. Architecture summary

Single-process, event-driven framework. A central `EventEngine`
(`vnpy/event/engine.py`, thread-safe `queue.Queue` + worker/timer threads) routes
typed `Event`s to handlers. A `MainEngine` (`vnpy/trader/engine.py`) is the
composition root owning pluggable **gateways** (broker adapters), **engines** (OMS,
risk, algo), and **apps** — all wired only through the event bus. Domain objects
(`vnpy/trader/object.py`) are dataclasses with computed global `vt_*` IDs; the
`Exchange` enum already includes `CME`, `GLOBEX`, `NYMEX`, `CBOT`. `OmsEngine`
passively caches the latest of everything with `get_*`/`get_all_*` queries.

> **Caveat:** README states the codebase was machine-translated from Chinese; log
> strings are garbled. Treat as a *pattern/reference* source — port deliberately.

## 3. Candidate features — ELITE / NOT-ELITE

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Event-driven core (`EventEngine` + `MainEngine` plugin arch) | `vnpy/event/engine.py`, `vnpy/trader/engine.py` | **ELITE** | Proven decoupled backbone; engine-plugin pattern maps onto QUANTFLO's per-team engines. |
| 2 | Normalized trader object model + OMS cache | `vnpy/trader/object.py`, `engine.py` (`OmsEngine`) | **ELITE** | Broker-agnostic order/trade/position schema + active-order tracking; `Exchange` enum already has CME/GLOBEX/CBOT. |
| 3 | Gateway adapter abstraction (`BaseGateway` + `LocalOrderManager`) | `vnpy/trader/gateway.py` | **ELITE** | Local↔system order-id reconciliation + out-of-order push buffering = the hard parts of live execution, solved. |
| 4 | Execution-algo framework (`AlgoTemplate` + TWAP/Iceberg/Sniper/…) | `vnpy/app/algo_trading/` | **ELITE** | Ready-made institutional order-slicing primitives; port cleanly to CME futures. |
| 5 | Local stop-order simulation (CTA engine) | `vnpy/app/cta_strategy/engine.py` (`check_stop_order`, `send_local_stop_order`), `base.py` (`StopOrder`) | **ELITE** | Broker-independent protective stops w/ native-stop fallback — essential when a CME route lacks native stops. |
| 6 | Data utils (`BarGenerator` + `ArrayManager`) | `vnpy/trader/utility.py` (l. 123–455) | **ELITE (pattern)** | Real-time tick→bar synthesis + rolling indicators for the data-engineering team. |
| 7 | Pre-trade risk gate (`RiskManagerEngine`) | `vnpy/app/risk_manager/engine.py` | **NOT-ELITE (code)** | Interception *pattern* is good, but it monkey-patches `send_order` (fragile global mutation) and limits are simplistic — adopt concept via proper middleware. |

### Rejected / NOT-ELITE (with reason)
- `vnpy/trader/converter.py` (`OffsetConverter`/`PositionHolding`) — China A-share/SHFE
  today-vs-yesterday offset machinery; CME futures are net-position. Rejected.
- Crypto/Chinese gateways (`binance`, `bitmex`, `okex`, `huobi`, `coinbase`, …) — wrong
  venue/asset class; keep only `alpaca`/`ib` as reference adapters.
- Qt/PySide UI (`vnpy/trader/ui/`, every app `ui/widget.py`, `vnpy/chart/`) — desktop GUI, irrelevant to an autonomous backend.
- `rpc_service`, `script_trader`, `data_recorder`, `csv_loader` apps — commodity conveniences.

## 4. Feasibility probe — **EXECUTED · PASS (elite features)**

- **Command:** `python -m pytest tests/test_import_all.py::CoreImportTest -v`
  (from `_research/pyalgotrader/`).
- **Env:** throwaway venv; `pip install numpy pytest TA-Lib qdarkstyle`.
- **Result:** `2 passed, 1 failed`.
  - `test_import_event_engine` → **PASS** (feature #1 core).
  - `test_import_main_engine` → **PASS** (features #1/#2: MainEngine + OmsEngine +
    object model load after TA-Lib wheel installed).
  - `test_import_ui` → **FAIL** (needs PyQt5) — this is the **rejected/NOT-ELITE**
    GUI layer, so the failure is expected and irrelevant to our extraction.
- **Direct import check** (`from vnpy.event import EventEngine; from vnpy.trader.engine
  import MainEngine, OmsEngine`) succeeded once `talib` was present.
- **Blocker found:** `vnpy/trader/utility.py` imports `talib` at module top, so any
  `MainEngine` import requires the TA-Lib C library (a Windows-prebuilt wheel
  resolved it here). Deeper algo/CTA probes (#4/#5) need a running gateway or local
  bar DB → deferred. Command for later: `set VNPY_TEST_ONLY_SQLITE=1 && python -m
  pytest tests/trader/test_database.py` and `python -m pytest tests/app/test_csv_loader.py`.

## 5. License-compatibility note

MIT → **direct port allowed**. Target QUANTFLO modules: `EventEngine`/object
model → `core` + `orchestration` transport; `BaseGateway` + `LocalOrderManager` →
`execution/`; `AlgoTemplate` + local stop-orders → `execution/` algos;
`BarGenerator`/`ArrayManager` → `teams/data_engineering`. Credit vnpy + pyalgotrader
in `NOTICE`. Avoid vendoring the GUI, converter, and crypto gateways.
