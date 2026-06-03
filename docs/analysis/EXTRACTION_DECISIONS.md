# QUANTFLO — Extraction Decisions (master table)

> **This document governs all future porting.** Nothing may be ported into QUANTFLO in
> any later phase unless it appears here with an **ELITE** verdict, a **target module**,
> a **target_phase**, and a concrete **verification_method**. Per the Phase 0 rules, a
> feature with no concrete verification_method **cannot** be marked ELITE, and a feature
> that will not run in its own source repo is rejected.
>
> The union of the per-source sections below **is** the master table.

## Legend

- **License / copyleft flag:** `MIT`/`Apache-2.0` = permissive; `GPL-3.0` = **COPYLEFT**;
  `AGPL-3.0` = **NETWORK-COPYLEFT** (strongest).
- **Clean-room?** `No` (permissive, direct port allowed) · `Partial` (port pure logic,
  clean-room the venue layer) · `MANDATORY` (GPL/AGPL — reimplement behavior from a
  written spec; never copy code).
- **Target phase:** P1 Data & Vault · P2 Research & Strategy · P3 Testing & Validation ·
  P4 Risk & Execution · P5 ModelOps & Monitoring · P6 Governance & Go-Live.
- **Probe:** **`✅ source PASS @ <SHA>`** = the feature's own upstream test ran GREEN at
  the pinned SHA via `.github/workflows/probe.yml` (CI run **26902471654**, 4/4 jobs
  green: freqtrade@`9eededca`, hummingbot@`91ff6bfa`, lumibot@`ed4886b1`,
  openalgo@`b9154f66`) — or, for quanttrader/pyalgotrader, a local executed probe.
  `⚠ best-effort` = ran in a non-gating continue-on-error step. Features with **no** such
  marker verify at their **port phase** (design-references, need broker/data creds, or
  not creds-free-unit-testable) — no ELITE feature rests on inspection alone. For
  COPYLEFT/AGPL sources a green source-probe only validates that the behavior is worth
  clean-room reimplementing; the clean-room reimpl is still the porting verification.

## Copyleft summary (requirement 2.4)

| Source | License | Flag | Rule |
|--------|---------|------|------|
| ruflo | MIT | permissive | Leverage directly (backbone). |
| quanttrader | Apache-2.0 | permissive | Direct port + attribution. |
| pyalgotrader | MIT | permissive | Direct port + attribution. |
| hummingbot | Apache-2.0 | permissive | Port pure-Python; clean-room venue layer. |
| **freqtrade** | **GPL-3.0** | **COPYLEFT** | **Clean-room MANDATORY.** No code copied. |
| **lumibot** | **GPL-3.0** | **COPYLEFT** | **Clean-room MANDATORY** (MIT/GPL conflict → counsel). |
| **openalgo** | **AGPL-3.0** | **NETWORK-COPYLEFT** | **Clean-room MANDATORY**, most cautious. |
| neural-trader plugin | MIT | permissive | **Rejected as dependency** (ADR 0002). |

---

## quanttrader — Apache-2.0 (clean-room: No)

| Feature | Elite | Clean-room | Target module | Phase | Verification method (real-data test) |
|---------|-------|-----------|---------------|-------|--------------------------------------|
| Brokerage abstraction (backtest↔live portability) | ELITE | No | `execution/` | P4 | **✅ source PASS** (local `pytest tests/test_strats.py`). Port: run a QUANTFLO strategy unchanged against sim broker + Tradovate-sim via one interface; assert identical code path. |
| Backtest simulated brokerage (fills, commission, STOP/trailing) | ELITE | No | testers (Team 3) | P3 | **✅ source PASS** (local `tests/test_strats.py`). Port: backtest ES 2023 OOS; assert fills + commission match a hand-computed buy&hold curve. |
| Event-driven backtest engine + no-look-ahead DataBoard | ELITE | No | testers (Team 3) | P3 | **✅ source PASS** (local `tests/test_strats.py`). Port: feed a look-ahead-trap dataset; assert engine never reads future bars. |
| Config-driven RiskManager pre-trade gate | ELITE | No | `teams/risk_compliance` | P4 | Port: submit orders breaching single_trade/total_loss limits; assert rejection + lock. (Local backtest used PassThroughRiskManager — limits verify at port.) |
| Futures-multiplier Position/PnL | ELITE | No | `core` accounting | P3 | **✅ source PASS** (local `tests/test_strats.py`). Port: 2-contract ES round-trip; assert PnL = (exit−entry)×ticks×$12.50×qty. |
| CME instrument metadata seed | ELITE (data) | No | `core/instruments` | **P0 done** | **✅ DONE** — unit test asserts ES=50/NQ=20/MES=5/MNQ=2 (`tests/test_instruments.py`). |
| IB native brokerage integration | ELITE-conditional | No | `execution/` | P4 | Port (if IB chosen): place bracket order on IB paper account; confirm fill. |

## pyalgotrader — MIT (clean-room: No)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Event-driven core (`EventEngine` + `MainEngine` plugins) | ELITE | No | `core` + `orchestration` | P1 | **✅ source PASS** (local `CoreImportTest`, 2 passed). Port: dispatch N events to M handlers under load; assert ordering + no loss. |
| Normalized object model + OMS cache | ELITE | No | `execution/` | P4 | **✅ source PASS** (local `CoreImportTest` MainEngine/OMS). Port: construct Order/Trade/Position; assert `vt_*` ids + active-order view. |
| Gateway adapter + `LocalOrderManager` | ELITE | No | `execution/` | P4 | Port: simulate out-of-order broker push; assert local↔sys id reconciliation. |
| Execution-algo framework (TWAP/Iceberg/Sniper) | ELITE | No | `execution/` | P4 | Port: run TWAP over a sim tick stream; assert child orders slice parent qty on schedule. |
| Local stop-order simulation | ELITE | No | `execution/` | P4 | Port: place local stop; cross it in sim; assert exactly one real order fired. |
| `BarGenerator` + `ArrayManager` | ELITE (pattern) | No | `teams/data_engineering` | P1 | Port: feed ticks; assert 1-min bars aggregate + ATR matches a reference. |

## hummingbot — Apache-2.0 (clean-room: Partial — venue layer)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Controller/Executor/Orchestrator split | ELITE | No (pure-py) | `strategies/` + `execution/` | P2/P4 | **✅ source PASS @ `91ff6bfa`** (run 26902471654: module import + `test_executor_orchestrator.py`). Port: controller emits CreateExecutorAction; assert orchestrator instantiates executor + aggregates PnL. |
| Triple-barrier risk envelope (TP/SL/time/trailing) | ELITE | No (pure-py) | `execution/` | P4 | **✅ source PASS @ `91ff6bfa`** (run 26902471654: `test_position_executor.py`). Port: open sim ES position; assert SL/TP/time-limit/trailing exits at correct prices. |
| Executor PnL/`PerformanceReport` + `PositionHold` netting | ELITE | No (pure-py) | `core` accounting | P3/P4 | **✅ source PASS @ `91ff6bfa`** (run 26902471654: exercised in `test_executor_orchestrator.py`). Port: net buys/sells; assert breakeven + realized/unrealized PnL. |
| Unified backtest/live from one strategy def | ELITE | No (pure-py) | testers (Team 3) | P3 | Port: replay an ES candle fixture through one config; assert Sharpe/drawdown == live-path action sequence. (No bundled OHLCV → not in source-probe.) |
| Connector + `ClientOrderTracker` + `InFlightOrder` SM | ELITE (pattern) | Partial | `execution/` broker driver | P4 | Port: feed OrderUpdate/TradeUpdate incl lost-order; assert 11-state transitions + reconciliation. |
| Paper-trade mode (fills vs live book) | ELITE (pattern) | Partial | testers/`execution` | P3/P4 | Port: run a strategy unmodified vs sim broker; assert same API surface as live. |
| MQTT remote control + telemetry plane | ELITE (pattern) | No (pure-py) | monitoring/governance | P5/P6 | Port: publish kill command over bus; assert trading loop halts + PerformanceReport telemetry emitted. (Needs a broker → not in source-probe.) |

## freqtrade — GPL-3.0 (clean-room: MANDATORY / COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Lookahead-bias detector | ELITE | MANDATORY | testers (Team 3) | P3 | **✅ source PASS @ `9eededca`** (run 26902471654: `tests/optimize/test_lookahead_analysis.py`). Clean-room reimpl at port: run on a known-biased strategy; assert it flags the leak. |
| Recursive-formula bias detector | ELITE | MANDATORY | testers (Team 3) | P3 | **✅ source PASS @ `9eededca`** (run 26902471654: `tests/optimize/test_recursive_analysis.py`). Clean-room reimpl at port: vary startup candles 199→1999; assert unstable EMA/RSI flagged. |
| Performance-metrics library | ELITE | MANDATORY | testers/monitoring | P3/P5 | **✅ source PASS @ `9eededca`** (run 26902471654: `tests/data/test_metrics.py`). Clean-room reimpl at port: assert Sharpe/Sortino/Calmar within 1e-6 of `empyrical` (NOT freqtrade output). |
| Protections framework (circuit-breakers) | ELITE | MANDATORY | `teams/risk_compliance` | P4 | **✅ source PASS @ `9eededca`** (run 26902471654: `tests/plugins/test_protections.py`). Clean-room reimpl at port: trigger N stoplosses in lookback; assert global lock-until set. |
| Hyperopt loss interface + objective catalog | ELITE (interface) | MANDATORY | strategy-creators/modelops | P2/P5 | **✅ source PASS @ `9eededca`** (run 26902471654: `tests/optimize/test_hyperoptloss.py`). Clean-room reimpl at port: assert smaller-is-better on two synthetic equity curves. |
| FreqAI continual-learning architecture | ELITE (arch) | MANDATORY | `teams/modelops` | P5 | **⚠ best-effort** (run 26902471654 extended step, non-gating). Clean-room reimpl at port: retrain scheduler + drift gate; assert retrain triggers at boundary + outliers rejected. |
| Backtest fill-realism (ideas only) | ELITE (ideas) | MANDATORY | testers (Team 3) | P3 | Clean-room reimpl at port: trailing-within-candle; assert exit price on a crafted candle == expected. (Not in source-probe.) |
| Producer/Consumer signal pub/sub | ELITE (pattern) | MANDATORY | data-eng/research | P1/P2 | Clean-room reimpl at port: publish a signal; assert all subscribers receive it. (Not in source-probe.) |

## lumibot — GPL-3.0 (clean-room: MANDATORY / COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Continuous-futures roll engine | ELITE | MANDATORY | `core/instruments` + data-eng | P1 | **✅ source PASS @ `ed4886b1`** (run 26902471654: `tests/test_futures_roll.py`). Clean-room reimpl at port: assert active ES contract == 8 bdays before 3rd-Friday, all 6 symbols. |
| DataBento futures-data integration | ELITE (vendor ref) | MANDATORY | `teams/data_engineering` | P1 | **✅ source PASS @ `ed4886b1`** (run 26902471654: `tests/test_continuous_futures_resolution.py` — resolution/front-month logic). Clean-room reimpl at port: resolve CONT_FUTURE ES→front-month + stitch across a roll. |
| Futures margin/PnL backtest engine | ELITE | MANDATORY | testers (Team 3) | P3 | **⚠ best-effort** (run 26902471654 MES-margin lookup step). Clean-room reimpl at port: margin table + multiplier MtM; assert MES margin=1300 + FIFO lot ledger keyed on expiry. |
| Strategy lifecycle base + executor | ELITE (design) | MANDATORY | strategies/execution | P2/P4 | Clean-room reimpl at port: assert before_market_opens→on_trading_iteration→after_market_closes order on a sim session. (Design-ref; not in source-probe.) |
| Broker ABC backtest↔live parity | ELITE (design) | MANDATORY | `execution/` | P4 | Clean-room reimpl at port: one abstraction; assert same strategy runs vs sim + IB-paper with no code change. (Needs creds; not in source-probe.) |

## openalgo — AGPL-3.0 (clean-room: MANDATORY / NETWORK-COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| SmartOrder target-position delta | ELITE | MANDATORY | `execution/` | P4 | **✅ source PASS @ `b9154f66`** (run 26902471654: `test/test_smartorder_logic.py`, the 12-case truth table — REQUIRED/gating step). Clean-room reimpl at port: assert flat→long, long→short flip, no-op deltas (spec, not code). |
| Broker plugin/capability dispatch | ELITE | MANDATORY | `execution/` | P4 | Clean-room reimpl at port: register a Tradovate adapter via capability manifest; assert dynamic dispatch to place_order. (Not in source-probe.) |
| Sandbox paper-trade mode-switch | ELITE | MANDATORY | testers/governance | P3/P4 | **⚠ best-effort / known-shadow** — `test/sandbox/` is an upstream-repo package-name collision (its own `sandbox/__init__.py` shadows the root `sandbox/`); it ran non-gating. NOT part of the extracted SmartOrder feature. Clean-room reimpl at port: assert analyze-mode flag routes orders to sim engine with identical request/response shape. |
| WS market-data normalization + ZMQ fanout | ELITE | MANDATORY | `data/` + data-eng | P1 | Clean-room reimpl at port: normalize→bus→fanout; assert one slow client doesn't block the feed; LTP/Quote/Depth modes. (Needs a feed; not in source-probe.) |
| Token-at-rest encryption + key hashing | ELITE (pattern) | MANDATORY | `core/config` vault / risk | P1 | Clean-room reimpl at port: Argon2 key-hash + Fernet token encrypt; assert plaintext never persisted; boot fails on weak pepper. |
| Stale-token auto-recovery | ELITE (pattern) | MANDATORY | `execution/` | P4 | Clean-room reimpl at port: simulate 401; assert fresh token fetched + single retry + caches invalidated. |
| In-process event bus | ELITE (pattern) | MANDATORY | `orchestration`/`state_bus` | P1 | Clean-room reimpl at port: publish OrderPlaced event; assert monitoring + governance subscribers fire without blocking trade path. |

## ruflo — MIT (backbone: leverage directly, not extract)

| Capability | Elite | Clean-room | Target module | Phase | Verification method |
|------------|-------|-----------|---------------|-------|---------------------|
| Swarm coordinator + spawn primitives | LEVERAGE | No | `orchestration` (Team 5) | P1 | Bridge Python Team-5 → ruflo via stdio MCP; spawn 10 agents; assert registry reflects 10. |
| MCP server bridge | LEVERAGE | No | `orchestration` | P1 | Call `swarm_init`/`agent_spawn` MCP tools from Python; assert success responses. |
| AgentDB / HNSW vector memory | LEVERAGE | No | `teams/modelops` + data-eng | P5 | Store + ANN-retrieve a market-regime vector; assert top-k recall (benchmark in-env, ignore marketing perf). |
| SONA self-learning + ReasoningBank | LEVERAGE | No | `teams/modelops` | P5 | Feed trajectory outcomes; assert routing accuracy improves on a held-out task set. |
| Consensus (Byzantine BFT) | LEVERAGE | No | governance (Team 10) | P6 | 3 agents vote on a trade decision with 1 faulty; assert correct decision survives (f<n/3). |

## neural-trader plugin — MIT (REJECTED as dependency; ADR 0002)

| Item | Verdict | Target | Phase | Verification method |
|------|---------|--------|-------|---------------------|
| External `neural-trader` engine | **REJECT** | — | — | Not adopted (scope mismatch + supply-chain hazard). |
| 4-agent risk-gated pipeline shape | Design reference only | research/modelops (design doc) | P2/P5 | Design review (not a code probe); if adopted: license-audit external pkg + clean-room CME agents. |

---

## Feasibility-probe status (requirement 2.6) — 4/4 CI jobs GREEN + 2 local

CI: `.github/workflows/probe.yml`, **run 26902471654**, all four jobs green.

| Source | Probe status | Evidence (what actually ran green) |
|--------|--------------|------------------------------------|
| quanttrader | **✅ PASS (local)** | `pytest tests/test_strats.py` → 1 passed (bundled `TEST.csv`, no creds). |
| pyalgotrader | **✅ PASS (local, elite features)** | `CoreImportTest` → 2 passed (event engine + MainEngine/OMS); only `test_import_ui` failed (PyQt5 = rejected feature). |
| ruflo | **PARTIAL (runtime present)** | Pinned `ruflo@3.10.31` installs + CLI boots; swarm unit suites deferred (need `tsc` build). Backbone, not an extraction target. |
| freqtrade | **✅ PASS @ `9eededca`** (run 26902471654) | `pytest` GREEN on metrics + lookahead + recursive bias detectors + protections + hyperopt-loss (5 ELITE features). FreqAI datakitchen = best-effort (non-gating). |
| hummingbot | **✅ PASS @ `91ff6bfa`** (run 26902471654) | V2 controller/executor/orchestrator imports OK; `test_executor_orchestrator.py` + `test_position_executor.py` (+ `test_rate_oracle.py`) GREEN → controller/executor split, triple-barrier, PnL-netting (3 ELITE). |
| lumibot | **✅ PASS @ `ed4886b1`** (run 26902471654) | `test_futures_roll.py` + `test_continuous_futures_resolution.py` GREEN → roll engine + DataBento resolution (2 ELITE). MES-margin lookup = best-effort. |
| openalgo | **✅ PASS @ `b9154f66`** (run 26902471654) | REQUIRED `test/test_smartorder_logic.py` GREEN → SmartOrder delta (1 ELITE). `test/sandbox/` = best-effort/known-shadow (upstream `test/sandbox/` package shadows root `sandbox/`), not part of the extracted feature. |
| neural-trader plugin | N/A (rejected) | No standalone runnable feature; engine rejected as dependency. |

**Status (requirement 4 — no feature ELITE on inspection alone):** every substantial
source now has an **executed** probe — quanttrader + pyalgotrader locally, and
freqtrade/hummingbot/lumibot/openalgo via CI **run 26902471654** (4/4 jobs green). The
**flagship, creds-free-testable ELITE features carry `✅ source PASS @ <SHA>`**. The
remaining ELITE rows (design-references like lumibot's lifecycle/broker-ABC, hummingbot's
connector/paper-trade/MQTT, openalgo's plugin-dispatch/WS/token/event-bus; freqtrade's
backtest-realism/pub-sub; FreqAI) are **not** creds-free-unit-testable in isolation —
their verification is a **port-phase real-data test** by nature, recorded per-row above.
For all COPYLEFT/AGPL sources the green source-probe only confirms the behavior is worth
**clean-room reimplementing**; the clean-room reimpl remains the porting verification.
Probe workspaces stayed isolated in `$RUNNER_TEMP`; **nothing was copied into `quantflo/`**.
