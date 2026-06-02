# Source Analysis — `hummingbot/hummingbot`

> QUANTFLO Stage 1 repo analysis. Real file paths relative to `_research/hummingbot/`.
> QUANTFLO scope: CME index futures (NQ MNQ ES MES YM MYM).

## 1. License (authoritative)

- **SPDX:** `Apache-2.0` (GitHub Licenses API + `LICENSE`).
- **Classification:** **PERMISSIVE.** Direct reuse/porting allowed.
- **`NOTICE` file:** none present in repo (verified) → no upstream NOTICE-propagation
  obligation beyond Apache §4(a)–(c): keep the license text with reused source, retain
  copyright notices, state significant changes.
- **Clean-room required?** **No (legally).** But **clean-room is preferable for the
  venue-touching layers** — the crypto connectors carry heavy Cython + REST/WS +
  collateral/funding baggage that would pollute a futures-only codebase. **Port the
  pure-Python V2 patterns directly; clean-room the broker adapters.**

## 2. Architecture summary

Mature event-driven Python framework with Cython hot-paths. A `Clock` drives
`TimeIterator`/`NetworkIterator` objects on tick. Exchanges are normalized behind a
`ConnectorBase` → `ExchangeBase`/`PerpetualDerivativePyBase` hierarchy emitting a fixed
`MarketEvent` vocabulary, with order state tracked via `ClientOrderTracker` over
`InFlightOrder`. The modern **Strategy V2** layer cleanly splits **Controllers**
(decide *what* — emit `ExecutorAction`s onto a queue) from **Executors** (decide *how*
— own order lifecycle + a triple-barrier risk envelope), wired by an
`ExecutorOrchestrator`. The same `*Config` dataclasses feed both a live
`MarketDataProvider` and a vectorized pandas `BacktestingEngineBase` — define once,
backtest and trade identically. Crypto/CEX/DEX-centric, but most V2 abstractions are
venue-agnostic.

| Path | Purpose |
|------|---------|
| `hummingbot/connector/` | broker abstraction; `connector_base.pyx`, `client_order_tracker.py` |
| `hummingbot/connector/test_support/` | `mock_paper_exchange.pyx`, `network_mocking_assistant.py` (creds-free testing) |
| `hummingbot/strategy_v2/controllers/` | `controller_base.py`, directional/market-making bases |
| `hummingbot/strategy_v2/executors/` | `executor_base.py`, `executor_orchestrator.py`, `position_executor/`, `twap_executor/`, `dca_executor/` |
| `hummingbot/strategy_v2/backtesting/` | `backtesting_engine_base.py`, executor simulators |
| `hummingbot/core/` | `clock.pyx`, `trading_core.py`, `rate_oracle/`, `utils/kill_switch.py` |
| `hummingbot/remote_iface/mqtt.py` | headless command/telemetry bus |
| `hummingbot/client/` | CLI app, status console, `performance.py` |

## 3. Candidate features — ELITE / NOT-ELITE

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Strategy V2 Controller/Executor/Orchestrator split | `strategy_v2/controllers/controller_base.py`, `executors/executor_base.py`, `executor_orchestrator.py`, `models/executor_actions.py` | **ELITE** | The action-queue boundary maps ~1:1 onto QUANTFLO strategy-creators (controllers) vs traders (executors); venue-agnostic. |
| 2 | Triple-Barrier risk envelope (TP/SL/time-limit/trailing) | `executors/position_executor/data_types.py` (`TripleBarrierConfig`, `TrailingStop`), `position_executor.py` | **ELITE** | Per-position bracketed risk is exactly what an index-futures execution layer needs; config is pure/instrument-neutral. |
| 3 | Unified backtest/live engine from one strategy def | `strategy_v2/backtesting/backtesting_engine_base.py`, `executors_simulator/position_executor_simulator.py` | **ELITE** | "Define once, backtest and trade identically" prevents sim/live drift. |
| 4 | Connector abstraction + `ClientOrderTracker` + `InFlightOrder` state machine | `connector/connector_base.pyx`, `exchange_py_base.py`, `client_order_tracker.py`, `core/data_type/in_flight_order.py` | **ELITE (pattern)** | Event vocabulary + 11-state order lifecycle + lost-order reconciliation = right shape for a CME broker adapter (Rithmic/CQG/IB). |
| 5 | Paper-trade mode (fills vs live order-book) | `connector/exchange/paper_trade/paper_trade_exchange.pyx`, `test_support/mock_paper_exchange.pyx` | **ELITE (pattern)** | Drop-in simulated broker with the live interface — essential for dry-run validation. |
| 6 | Executor PnL / `PerformanceReport` + `PositionHold` netting | `executors/executor_orchestrator.py`, `models/executors_info.py`, `client/performance.py` | **ELITE** | Clean realized/unrealized split w/ breakeven netting; currency-agnostic math. |
| 7 | MQTT remote interface (headless command + telemetry) | `remote_iface/mqtt.py`, `messages.py` | **ELITE (pattern)** | A control/telemetry plane decoupled from the trading loop — orchestration + monitoring + kill-switch. |
| 8 | RateOracle (connector-fallback price resolution) | `core/rate_oracle/rate_oracle.py`, `sources/` | **NOT-ELITE** | Built for cross-token FX conversion; single-quote USD futures don't need it. |

### Rejected / NOT-ELITE (with reason)
- Gateway/AMM/DEX layer (`core/gateway/`, `data_feed/amm_gateway_data_feed.py`) — blockchain-swap specific; zero CME relevance.
- Funding-rate / perpetual machinery (`core/data_type/funding_info.py`, `v2_funding_rate_arb.py`) — no funding payments in CME index futures.
- XEMM / cross-exchange / XRPL / Injective connectors — venue/crypto-arb specific.
- `silly_commands.py` / `silly_resources/` — ASCII-art easter eggs; noise.
- `parrot.py` / `connector_metrics_collector.py` — phone-home volume telemetry to Hummingbot servers; undesirable for a private platform.
- RateOracle (#8) — FX-conversion oriented.

## 4. Feasibility probe — **DEFERRED (commands specified; blocker recorded)**

The V2 abstractions are covered by mock-driven unit tests needing no creds, but
**blocker:** hummingbot requires a Cython compile/build of the package before its
test suite runs (`setup.py` + `compile`), which is the install friction on Windows.
Deferred. **Exact creds-free commands (post-build):**

- Feature #1/#6: `python -m pytest test/hummingbot/strategy_v2/executors/test_executor_orchestrator.py`
- Feature #2: `python -m pytest test/hummingbot/strategy_v2/executors/position_executor/test_position_executor.py`
- Feature #8: `python -m pytest test/hummingbot/core/rate_oracle/test_rate_oracle.py`

**Note on #3 (backtest):** the engine is provable but **no OHLCV fixtures ship** and
there is no `test/.../backtesting/` dir — `BacktestingDataProvider` fetches candles
from exchanges. A probe must supply a CSV/parquet candle fixture into
`prepare_market_data`; the simulator math (`position_executor_simulator.py`) is pure
pandas and inspectable offline. Features #1–#7 marked **ELITE (probe deferred)**.

## 5. License-compatibility note (Apache-2.0)

Permissive: **direct port of the pure-Python V2 patterns is acceptable** (controllers,
executors, orchestrator, triple-barrier configs, order-tracker/`InFlightOrder` state
machine, backtest summarize logic) — preserve license headers + add an Apache notice
in QUANTFLO's THIRD-PARTY attributions. **Clean-room the connector/broker adapters and
any executor adapted to CME futures**, for two non-legal reasons: the crypto code
carries Cython/REST/WS/collateral baggage, and reimplementing forces the interface to
match the futures broker (tick value, margin, sessions, contract roll). Target modules:
controllers → `strategies/`; executors + triple-barrier → `execution/`; order-tracker
pattern → `execution/` broker driver; MQTT control plane → `orchestration/` + monitoring.
