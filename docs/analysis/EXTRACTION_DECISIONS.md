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
- **Probe:** `PASS (executed)` · `deferred (cmd specified)` — see each
  `*_analysis.md` and §Feasibility-probe status.

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
| Brokerage abstraction (backtest↔live portability) | ELITE | No | `execution/` | P4 | Run a QUANTFLO strategy unchanged against sim broker + Tradovate-sim via one interface; assert identical code path; **base probe PASS (executed)**. |
| Backtest simulated brokerage (fills, commission, STOP/trailing) | ELITE | No | testers (Team 3) | P3 | Backtest ES 2023 OOS bars; assert fills + commission match a hand-computed buy&hold equity curve. |
| Event-driven backtest engine + no-look-ahead DataBoard | ELITE | No | testers (Team 3) | P3 | Feed a look-ahead-trap dataset; assert engine never reads future bars (bias test green). |
| Config-driven RiskManager pre-trade gate | ELITE | No | `teams/risk_compliance` | P4 | Submit orders breaching single_trade/total_loss limits; assert rejection + lock. |
| Futures-multiplier Position/PnL | ELITE | No | `core` accounting | P3 | 2-contract ES round-trip; assert PnL = (exit−entry)×ticks×$12.50×qty. |
| CME instrument metadata seed | ELITE (data) | No | `core/instruments` | **P0 done** | Unit test asserts ES=50/NQ=20/MES=5/MNQ=2 — **DONE** (`tests/test_instruments.py`). |
| IB native brokerage integration | ELITE-conditional | No | `execution/` | P4 | (If IB chosen) place bracket order on IB paper account; confirm fill. |

## pyalgotrader — MIT (clean-room: No)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Event-driven core (`EventEngine` + `MainEngine` plugins) | ELITE | No | `core` + `orchestration` | P1 | Dispatch N events to M handlers under load; assert ordering + no loss; **import probe PASS (executed)**. |
| Normalized object model + OMS cache | ELITE | No | `execution/` | P4 | Construct Order/Trade/Position; assert `vt_*` ids + active-order view correct. |
| Gateway adapter + `LocalOrderManager` | ELITE | No | `execution/` | P4 | Simulate out-of-order broker push; assert local↔sys id reconciliation. |
| Execution-algo framework (TWAP/Iceberg/Sniper) | ELITE | No | `execution/` | P4 | Run TWAP over a sim tick stream; assert child orders slice parent qty on schedule. |
| Local stop-order simulation | ELITE | No | `execution/` | P4 | Place local stop; cross it in sim; assert exactly one real order fired. |
| `BarGenerator` + `ArrayManager` | ELITE (pattern) | No | `teams/data_engineering` | P1 | Feed ticks; assert 1-min bars aggregate correctly + ATR matches a reference. |

## hummingbot — Apache-2.0 (clean-room: Partial — venue layer)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Controller/Executor/Orchestrator split | ELITE | No (pure-py) | `strategies/` + `execution/` | P2/P4 | Controller emits CreateExecutorAction; assert orchestrator instantiates executor + aggregates PnL (mirror `test_executor_orchestrator.py`). |
| Triple-barrier risk envelope (TP/SL/time/trailing) | ELITE | No (pure-py) | `execution/` | P4 | Open sim ES position; assert SL/TP/time-limit/trailing exits at correct prices. |
| Unified backtest/live from one strategy def | ELITE | No (pure-py) | testers (Team 3) | P3 | Replay an ES candle fixture through one config; assert Sharpe/drawdown == live-path action sequence. |
| Connector + `ClientOrderTracker` + `InFlightOrder` SM | ELITE (pattern) | Partial | `execution/` broker driver | P4 | Feed OrderUpdate/TradeUpdate incl lost-order; assert 11-state transitions + reconciliation. |
| Paper-trade mode (fills vs live book) | ELITE (pattern) | Partial | testers/`execution` | P3/P4 | Run a strategy unmodified vs sim broker; assert same API surface as live. |
| Executor PnL/`PerformanceReport` + `PositionHold` netting | ELITE | No (pure-py) | `core` accounting | P3/P4 | Net buys/sells; assert breakeven + realized/unrealized PnL. |
| MQTT remote control + telemetry plane | ELITE (pattern) | No (pure-py) | monitoring/governance | P5/P6 | Publish kill command over bus; assert trading loop halts + PerformanceReport telemetry emitted. |

## freqtrade — GPL-3.0 (clean-room: MANDATORY / COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Lookahead-bias detector | ELITE | MANDATORY | testers (Team 3) | P3 | Clean-room reimpl; run on a known-biased strategy; assert it flags the leak. |
| Recursive-formula bias detector | ELITE | MANDATORY | testers (Team 3) | P3 | Reimpl; vary startup candles 199→1999; assert unstable EMA/RSI flagged. |
| Performance-metrics library | ELITE | MANDATORY | testers/monitoring | P3/P5 | Reimpl Sharpe/Sortino/Calmar; assert within 1e-6 of `empyrical` (a clean reference, NOT freqtrade output). |
| Protections framework (circuit-breakers) | ELITE | MANDATORY | `teams/risk_compliance` | P4 | Reimpl stoploss-guard; trigger N stoplosses in lookback; assert global lock-until set. |
| Hyperopt loss interface + objective catalog | ELITE (interface) | MANDATORY | strategy-creators/modelops | P2/P5 | Reimpl interface + Sharpe loss; assert smaller-is-better on two synthetic equity curves. |
| FreqAI continual-learning architecture | ELITE (arch) | MANDATORY | `teams/modelops` | P5 | Reimpl retrain scheduler + drift gate; on a rolling window assert retrain triggers at boundary + outliers rejected. |
| Backtest fill-realism (ideas only) | ELITE (ideas) | MANDATORY | testers (Team 3) | P3 | Reimpl trailing-within-candle; assert exit price on a crafted candle == expected. |
| Producer/Consumer signal pub/sub | ELITE (pattern) | MANDATORY | data-eng/research | P1/P2 | Reimpl pub/sub; publish a signal; assert all subscribers receive it. |

## lumibot — GPL-3.0 (clean-room: MANDATORY / COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Continuous-futures roll engine | ELITE | MANDATORY | `core/instruments` + data-eng | P1 | Reimpl roll rules; assert active ES contract on a date == 8 bdays before 3rd-Friday, all 6 symbols (behavior cross-check vs `tests/test_futures_roll.py`). |
| Futures margin/PnL backtest engine | ELITE | MANDATORY | testers (Team 3) | P3 | Reimpl margin table + multiplier MtM; assert MES margin=1300 + FIFO lot ledger keyed on expiry. |
| Strategy lifecycle base + executor | ELITE (design) | MANDATORY | strategies/execution | P2/P4 | Reimpl hook set; assert before_market_opens→on_trading_iteration→after_market_closes order on a sim session. |
| Broker ABC backtest↔live parity | ELITE (design) | MANDATORY | `execution/` | P4 | One abstraction; assert same strategy runs vs sim + IB-paper with no code change. |
| DataBento futures-data integration | ELITE (vendor ref) | MANDATORY | `teams/data_engineering` | P1 | Resolve CONT_FUTURE ES→front-month on a date; stitch across a roll; assert continuous series. |

## openalgo — AGPL-3.0 (clean-room: MANDATORY / NETWORK-COPYLEFT)

| Feature | Elite | Clean-room | Target module | Phase | Verification method |
|---------|-------|-----------|---------------|-------|---------------------|
| Broker plugin/capability dispatch | ELITE | MANDATORY | `execution/` | P4 | Reimpl plugin loader; register a Tradovate adapter via capability manifest; assert dynamic dispatch to place_order. |
| SmartOrder target-position delta | ELITE | MANDATORY | `execution/` | P4 | Reimpl from the 12-case truth table; assert flat→long, long→short flip, and no-op deltas (spec from `test_smartorder_logic.py`, not code). |
| Sandbox paper-trade mode-switch | ELITE | MANDATORY | testers/governance | P3/P4 | Reimpl analyze-mode flag; assert order routes to sim engine with identical request/response shape. |
| WS market-data normalization + ZMQ fanout | ELITE | MANDATORY | `data/` + data-eng | P1 | Reimpl normalize→bus→fanout; assert one slow client doesn't block the feed; LTP/Quote/Depth modes. |
| Token-at-rest encryption + key hashing | ELITE (pattern) | MANDATORY | `core/config` vault / risk | P1 | Reimpl Argon2 key-hash + Fernet token encrypt; assert plaintext never persisted; boot fails on weak pepper. |
| Stale-token auto-recovery | ELITE (pattern) | MANDATORY | `execution/` | P4 | Simulate 401; assert fresh token fetched + single retry + caches invalidated. |
| In-process event bus | ELITE (pattern) | MANDATORY | `orchestration`/`state_bus` | P1 | Publish OrderPlaced event; assert monitoring + governance subscribers fire without blocking trade path. |

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

## Feasibility-probe status (requirement 2.6)

| Source | Probe status | Evidence |
|--------|--------------|----------|
| quanttrader | **PASS (executed)** | `pytest tests/test_strats.py` → 1 passed (bundled `TEST.csv`, no creds). |
| pyalgotrader | **PASS (executed, elite features)** | `CoreImportTest` → 2 passed (event engine + MainEngine/OMS); only `test_import_ui` failed (PyQt5 = rejected feature). |
| ruflo | **PARTIAL (runtime present)** | Pinned `ruflo@3.10.31` installs + CLI boots (loads ONNX model); swarm unit suites deferred (need `tsc` build). |
| freqtrade | deferred (cmds specified) | Bundled `tests/testdata` + tests; blocker = heavy install / TA-Lib / FreqAI ML stack. |
| lumibot | deferred (cmds specified) | `tests/test_futures_roll.py` creds-free; blocker = heavy broker-SDK install; end-to-end futures backtest needs DataBento key. |
| openalgo | deferred (cmds specified) | `test/test_smartorder_logic.py` creds-free; blocker = full Flask/uv app install. |
| hummingbot | deferred (cmds specified) | mock-based V2 tests creds-free; blocker = Cython build of the package. |
| neural-trader plugin | N/A (rejected) | No standalone runnable feature; engine rejected as dependency. |

**Honest gap (carried to gate §G):** 2 of 6 substantial repos have **executed** probes;
4 are **deferred with exact creds-free commands** (and are GPL/AGPL clean-room targets
where the probe validates the source before reimplementation). ELITE features on
deferred repos are tagged "(probe deferred)" in their analysis reports. Recommendation:
stand up a dedicated Linux probe-CI image (with TA-Lib, Cython build, `uv`, and a
DataBento sim key) and execute every command above before the corresponding port phase
begins; a feature whose probe then fails is demoted from ELITE.
