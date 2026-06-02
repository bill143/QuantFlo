# Source Analysis — `freqtrade/freqtrade`

> QUANTFLO Stage 1 repo analysis. Real file paths relative to `_research/freqtrade/`.
> QUANTFLO scope: CME index futures (NQ MNQ ES MES YM MYM).

## 1. License (authoritative)

- **SPDX:** `GPL-3.0` (GitHub Licenses API + `LICENSE` = full GNU GPL v3 text).
- **Classification:** **STRONG COPYLEFT.**
- **Clean-room required?** **YES — MANDATORY.** No freqtrade source may be copied,
  pasted, adapted, or paraphrased into QUANTFLO. Only *ideas/algorithms/interface
  shapes* may be reimplemented from a written spec by someone who has not pasted the
  original code. **`COPYLEFT` flag applies to every feature below.**

## 2. Architecture summary

Mature, crypto/ccxt-centric Python trading bot. Single `freqtrade/` package with
clean subsystem boundaries and a resolver/plugin pattern (strategies, protections,
pairlists, hyperopt losses, FreqAI models are all dynamically loaded via abstract
interfaces, so individual *ideas* are decoupled). Bundles substantial offline test
data (`tests/testdata/` — feather/JSON OHLCV, futures + funding + mark-price,
orderflow, backtest results) so most analytical features run with no credentials.
The exchange/execution layers are crypto-CEX specific (irrelevant to CME), but the
**analytical / risk / ML** layers are highly relevant — as *clean-room blueprints*.

| Path | Purpose |
|------|---------|
| `freqtrade/optimize/` | backtesting engine, hyperopt, reports |
| `freqtrade/optimize/analysis/` | lookahead-bias + recursive-formula bias detectors |
| `freqtrade/optimize/hyperopt_loss/` | 13 pluggable objective functions |
| `freqtrade/freqai/` | ML feature pipeline, continual learning, RL, drift cleaning |
| `freqtrade/data/metrics.py` | Sharpe/Sortino/Calmar/CAGR/SQN/drawdown math |
| `freqtrade/plugins/protections/` | risk circuit-breakers |
| `freqtrade/strategy/` | `IStrategy` callback interface |
| `freqtrade/rpc/` | Telegram/Discord/webhook + FastAPI REST/WebSocket |
| `tests/testdata/` | bundled OHLCV/futures/orderflow for offline runs |

## 3. Candidate features — ELITE / NOT-ELITE (all COPYLEFT → clean-room)

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Lookahead-bias detector | `optimize/analysis/lookahead.py` (+ `base_analysis.py`, `lookahead_helpers.py`) | **ELITE** | Catches strategies that "peek" at future candles — the #1 silent backtest killer; instrument-agnostic. |
| 2 | Recursive-formula / startup-candle bias detector | `optimize/analysis/recursive.py` (+ `recursive_helpers.py`) | **ELITE** | Exposes unstable warmup indicators (EMA/RSI) that make live ≠ backtest; pure numerical. |
| 3 | Performance-metrics library | `data/metrics.py` | **ELITE** | Exchange-agnostic Sharpe/Sortino/Calmar/CAGR/expectancy/SQN/drawdown for testers + monitoring. |
| 4 | Protections framework (risk circuit-breakers) | `plugins/protections/iprotection.py` + `stoploss_guard.py`, `max_drawdown_protection.py`, `cooldown_period.py`, `protectionmanager.py` | **ELITE** | `global_stop`/`stop_per_pair` returning a lock-until maps ~1:1 to risk-compliance + kill-switch. |
| 5 | Hyperopt loss-function interface + objective catalog | `optimize/hyperopt_loss/hyperopt_loss_interface.py` + 13 impls | **ELITE (interface)** | Reusable risk-adjusted objective taxonomy for strategy-creators/modelops (not the Optuna plumbing). |
| 6 | FreqAI continual-learning + drift-cleaning architecture | `freqai/freqai_interface.py` (`continual_learning`, retrain scheduler), `data_kitchen.py` (recency weighting, SVM/DBSCAN outlier removal, DI), `data_drawer.py` (model registry) | **ELITE (architecture)** | The retrain-scheduler + drift-gate + model-registry shape is exactly the modelops blueprint. |
| 7 | Backtest fill-realism engine (trailing-within-candle, ROI ladder, DCA, order-replace) | `optimize/backtesting.py` (`backtest_loop`, `_check_adjust_trade_for_candle`, `_get_close_rate_for_*`, `check_order_replace`) | **ELITE (ideas only)** | Fill realism worth reimplementing — but 1,908 ln, deeply coupled to `persistence/` ORM; **port concepts, never structure.** |
| 8 | Producer/Consumer signal-sharing (auth WebSocket pub/sub) | `rpc/external_message_consumer.py`, `rpc/api_server/ws/` | **ELITE (pattern)** | Fan research/strategy signals to many execution agents — orchestration + data-eng. |

### Rejected / NOT-ELITE (with reason)
- `freqtrade/exchange/*` (binance/bybit/okx/kraken/hyperliquid) — crypto-CEX/ccxt adapters; no CME/IB/Rithmic relevance.
- `_run_funding_fees`, `freqtrade/leverage/`, funding/mark-price download — perpetual-swap concepts that don't exist for CME index futures.
- `freqtrade/plugins/pairlist/*` (VolumePairList…) — dynamic scan of thousands of crypto pairs; QUANTFLO trades a fixed 6-symbol universe.
- `rpc/telegram.py` (2,285 ln) / `discord.py` — generic chat-bot glue; low value unless a Telegram console is a product requirement.
- `data/converter/orderflow.py`, `trade_converter_kraken.py` — crypto-trade-feed specific.
- FreqAI `RL/*` reward envs — too entangled to beat a standard RL lib.
- `Edge` positioning — **removed** in this version; historical.

## 4. Feasibility probe — **DEFERRED (commands specified; blocker recorded)**

All flagship analytical features have bundled offline data + tests (no creds), but
running them requires a full freqtrade install. **Blocker:** heavy dependency stack
(pandas/scipy/ccxt + TA-Lib C lib); the FreqAI probe additionally needs the
`requirements-freqai.txt` ML stack (LightGBM/XGBoost/torch). On Windows the native
build is non-trivial. Deferred to the dedicated clean-room validation step in the
target phase. **Exact creds-free commands (validate the source before reimplementing):**

- Feature #1: `pytest tests/optimize/test_lookahead_analysis.py`
- Feature #2: `pytest tests/optimize/test_recursive_analysis.py`
- Feature #3: `pytest tests/data/test_metrics.py`
- Feature #4: `pytest tests/plugins/test_protections.py`
- Feature #5: `pytest tests/optimize/test_hyperoptloss.py`
- Feature #6: `pytest tests/freqai/test_freqai_datakitchen.py` (needs `requirements-freqai.txt`)
- Feature #7: `pytest tests/optimize/test_backtesting.py tests/optimize/test_backtest_detail.py`
- Feature #8: `pytest tests/rpc/test_rpc_emc.py`

All consume `tests/testdata/` only. These probes run in the clean-room validation
phase; until then features #1–#8 are marked **ELITE (probe deferred)**.

## 5. License-compatibility note (GPL-3.0)

**Clean-room is mandatory.** Lowest-risk targets (small, self-contained, idea-level):
the metrics formulas (#3), the protection interface (#4), the hyperopt-loss interface +
objective taxonomy (#5), and the two bias detectors (#1, #2). **Too entangled to
reimplement structurally** (port concepts only): the backtesting engine
(`backtesting.py`) and FreqAI RL envs — both deeply coupled to `freqtrade/persistence/`
Trade/Order ORM. Governance note: any feature reaching into `persistence/` carries the
highest copyleft-entanglement risk and must be specced fresh, never mirrored.
