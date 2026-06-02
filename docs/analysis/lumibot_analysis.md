# Source Analysis — `Lumiwealth/lumibot`

> QUANTFLO Stage 1 repo analysis. Real file paths relative to `_research/lumibot/`.
> QUANTFLO scope: CME index futures (NQ MNQ ES MES YM MYM).

## 1. License (authoritative)

- **SPDX:** `GPL-3.0` (GitHub Licenses API + `LICENSE` = full GNU GPL v3 text).
- **⚠️ Conflict flagged:** `setup.py` declares `license="MIT"` with an MIT classifier
  and `README.md` shows an MIT badge — but the actual `LICENSE` file is GPL-3.0. This
  contradiction is a legal hazard.
- **Classification (per the LICENSE file, the controlling document):** **STRONG
  COPYLEFT.** Treat as **GPL-3.0**.
- **Clean-room required?** **YES — MANDATORY.** Reimplement *behavior* only (e.g.
  "ES rolls 8 business days before the 3rd-Friday expiry"), never the code.
  **Recommendation: confirm licensing intent with counsel given the MIT/GPL
  contradiction before relying on anything from this repo.**

## 2. Architecture summary

Mature layered Python framework: a `Strategy` base (lifecycle hooks) on top of
pluggable `Broker` and `DataSource` abstractions, wired by a `Trader` runner +
`StrategyExecutor` event loop. The same `Strategy` subclass runs unmodified in
backtest or live — only the broker/data pairing changes. Backtesting = a
`BacktestingBroker` (fill/margin/PnL sim) + `DataSourceBacktesting` subclasses.
**Futures are first-class:** a continuous-futures roll engine, per-symbol CME margin
tables, and multiplier-aware mark-to-market PnL — directly covering QUANTFLO's exact
universe. Code is heavily monolithic (`strategy.py` ~5,800 ln, `broker.py` ~3,000,
`backtesting_broker.py` ~4,450) — far over the 800-line guideline, a structural
warning for any port.

| Path | Purpose |
|------|---------|
| `lumibot/strategies/` | `Strategy` base + executor event loop |
| `lumibot/brokers/` | broker abstraction + concretes (alpaca, IB, tradier, tradovate…) |
| `lumibot/data_sources/` | data-source abstraction (yahoo, polygon, databento, IBKR…) |
| `lumibot/backtesting/` | `BacktestingBroker` + per-source backtest data |
| `lumibot/entities/` | `Asset`, `Order`, `Position`, `Bars` |
| `lumibot/tools/futures_roll.py` | **CME continuous-futures roll engine** |
| `data/` | bundled CSVs (SPY/TLT/GLD…) + `ibkr_symbol_lookup/us_futures_roots.csv` |

## 3. Candidate features — ELITE / NOT-ELITE (all COPYLEFT → clean-room)

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Continuous-futures roll engine | `tools/futures_roll.py`, `entities/asset.py` (l.~608–877), `tools/futures_symbols.py` | **ELITE** | `ROLL_RULES` literally lists ES/MES/NQ/MNQ/YM/MYM (l.40–43) — QUANTFLO's exact universe; correct CME roll semantics are non-trivial and core. |
| 2 | Futures-aware backtest fill + margin/PnL engine | `backtesting/backtesting_broker.py` (margin table l.35–130; `_realize_futures_pnl` l.~1920; multiplier handling l.1636/1703–1720) | **ELITE** | Models futures as margin instruments w/ multiplier MtM + FIFO lot ledger keyed on expiration; CME margin table for our symbols. |
| 3 | Strategy lifecycle base + executor | `strategies/strategy.py` (hooks l.~5071–5500), `strategy_executor.py` | **ELITE (design ref)** | Proven hook taxonomy (`on_trading_iteration`, `before_market_opens`, `on_bot_crash`, `on_abrupt_closing`) — crash/abrupt hooks map to kill-switch. |
| 4 | Broker ABC spanning live + backtest | `brokers/broker.py` (l.~684–830), `interactive_brokers.py` | **ELITE (design ref)** | One abstraction serving sim + live = backtest/live parity. IBKR is the only listed broker trading CME index futures. |
| 5 | DataBento institutional futures-data integration | `tools/databento_helper.py` (continuous resolution + front-month stitching), `backtesting/databento_backtesting_*.py` | **ELITE (vendor ref)** | DataBento is the institutional CME feed; contract-resolution + roll-stitching is the right pattern. |
| 6 | QuantStats tearsheet / reporting | `tools/indicators.py` (`create_tearsheet`, `stats_summary`) | **NOT-ELITE** | Thin QuantStats wrapper; QUANTFLO can call QuantStats directly without porting GPL code. |
| 7 | Drift-rebalancer portfolio logic | `components/drift_rebalancer_logic.py` | **NOT-ELITE** | Equity/crypto basket rebalancing; QUANTFLO trades correlated index futures where sizing/risk matters more. |

### Rejected / NOT-ELITE (with reason)
- AI multi-agent runtime (`components/agents/manager.py` ~2,080 ln) — generic LLM-orchestration; QUANTFLO defines its own agent contracts (and is on ruflo). Reference only.
- Non-CME brokers/data (ccxt, bitunix, projectx, tradovate-crypto, schwab, alpaca-stock, forex) — out of scope.
- Options/multileg (`black_scholes.py`, `chains.py`, iron-condor tests) — no options in QUANTFLO.
- ThetaData split/dividend corporate-action handling — irrelevant to index futures.
- Macro helpers (`macro/fred.py`, `vix_helper.py`, `perplexity_helper.py`) — thin API wrappers, rebuild trivially.
- Smart-limit execution (`entities/smart_limit.py`) — ~175 ln; too thin to be "elite" (concept noted).

## 4. Feasibility probe — **CI-DEFINED: `probe.yml` job `lumibot-probe` @ `ed4886b1` (pending manual dispatch)**

The flagship roll engine (#1) has **credential-free** unit tests; the end-to-end
futures backtest (#2) needs a DataBento key (its `tests/backtest/test_futures_*.py`
are `@pytest.mark.apitest`) and **no futures bars ship** in `data/`. **Blocker:**
installing lumibot pulls a large set of broker/data SDKs. Deferred.
**Exact creds-free commands (validate the source before clean-room):**

- Feature #1: `pytest tests/test_futures_roll.py tests/test_continuous_futures_resolution.py -v`
- Feature #2 (margin sub-logic only): `python -c "from lumibot.entities import Asset; from lumibot.backtesting.backtesting_broker import get_futures_margin_requirement as g; print(g(Asset('MES', asset_type=Asset.AssetType.FUTURE)))"` → expect `1300`
- Feature #2 (end-to-end fill/PnL): requires synthesizing a small `PandasData` feed — clean-room reimplement, do not reuse code.

Features #1–#5 marked **ELITE (verification → `probe.yml` CI, pending run)**.

## 5. License-compatibility note (GPL-3.0)

**Clean-room mandatory** and the MIT/GPL contradiction must be resolved with counsel.
Highest-value clean-room targets — reimplement *behavior*, not code: the roll rules
(#1, "ES/MES/NQ/MNQ/YM/MYM roll 8 business days before the 3rd-Friday expiry on the
Mar/Jun/Sep/Dec cycle"), the CME margin table values (#2), and the lifecycle hook
taxonomy (#3). Target modules: roll engine → `core/instruments` + `teams/data_engineering`;
margin/PnL → testers (Team 3) backtest + `core` accounting; lifecycle hooks → `orchestration`
+ `execution`; DataBento pattern → `teams/data_engineering`.
