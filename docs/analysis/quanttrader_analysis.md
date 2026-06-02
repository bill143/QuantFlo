# Source Analysis — `letianzj/quanttrader`

> QUANTFLO Stage 1 repo analysis. Evidence is cited as real file paths relative to
> the repo root (`_research/quanttrader/`). Verdicts are for QUANTFLO's scope:
> autonomous trading of CME index futures (NQ, MNQ, ES, MES, YM, MYM).

## 1. License (authoritative)

- **SPDX:** `Apache-2.0` (GitHub Licenses API + `LICENSE` file head).
- **Classification:** **PERMISSIVE.** Direct reuse/porting is allowed.
- **Obligations:** retain the Apache-2.0 license + copyright, state changes to any
  copied file, include a `NOTICE` if redistributing. Author: **Letian Wang**
  (`letian.zj@gmail.com`), v0.6.0.
- **Clean-room required?** **No** (permissive). Porting code directly is legally
  fine; we will still re-shape interfaces to the futures domain.

## 2. Architecture summary

Pure-Python (no Cython), event-driven backtest **and** live library for
equities/futures/FX/options via Interactive Brokers (`ibapi`). ~30 small modules
under `quanttrader/`. Everything flows through one `Event`/`EventType` enum
(`quanttrader/event/event.py`) and a shared set of managers (`StrategyManager`,
`OrderManager`, `PositionManager`, `RiskManager`, `DataBoard`, `PerformanceManager`).

**Key elite trait — "same code for backtest and live": PARTIALLY TRUE (verified).**
There are two engine classes — `BacktestEventEngine`
(`quanttrader/event/backtest_event_engine.py`, synchronous loop) and
`LiveEventEngine` (`quanttrader/event/live_event_engine.py`, threaded). They are
**not** the same class, but the `StrategyBase`, managers, and `BrokerageBase`
(`quanttrader/brokerage/brokerage_base.py`) are reused unchanged; a strategy is
swapped between `BacktestBrokerage` and `InteractiveBrokers` with no code change.
Backtest streaming is look-ahead-safe: `DataBoard.get_hist_price(symbol, ts)`
returns data only up to the current timestamp.

| Path | Purpose |
|------|---------|
| `quanttrader/event/` | event types + backtest loop + live thread |
| `quanttrader/brokerage/` | `brokerage_base.py`, `backtest_brokerage.py`, `ib_brokerage.py` |
| `quanttrader/strategy/` | `strategy_base.py`, `strategy_manager.py` (multi-strategy + risk gate) |
| `quanttrader/position/` | `position.py` (futures-multiplier PnL), `position_manager.py` |
| `quanttrader/risk/` | `risk_manager.py` (config limits); `margin_manager.py` = **empty stub** |
| `quanttrader/data/` | `data_board.py`, backtest/live feeds |
| `quanttrader/performance/` | pyfolio-format equity/positions/trades |
| `examples/instrument_meta.yaml` | ES/NQ/MES/MNQ multipliers + margins (GLOBEX) |
| `tests/test_data/TEST.csv` | bundled daily OHLCV (1,761 rows) used by the probe |

## 3. Candidate features — ELITE / NOT-ELITE

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Brokerage abstraction (backtest↔live portability) | `brokerage/brokerage_base.py`, `backtest_brokerage.py`, `ib_brokerage.py` | **ELITE** | The clean seam letting testers + traders share strategy code with zero divergence. |
| 2 | Backtest simulated brokerage (fills, commission, STOP/trailing crossing) | `brokerage/backtest_brokerage.py` | **ELITE** | Directly reusable futures fill+commission sim (FUT = $2.01/contract); STOP/trailing logic is what intraday NQ/ES backtests need. |
| 3 | Event-driven backtest engine + look-ahead-safe DataBoard | `backtest_engine.py`, `event/backtest_event_engine.py`, `data/data_board.py` | **ELITE** | Correct, non-trivial no-look-ahead bar backtest wiring (MtM-before-update). |
| 4 | Config-driven multi-limit RiskManager (pre-trade gate) | `risk/risk_manager.py`, `risk/risk_manager_base.py` | **ELITE** | Per-strategy + portfolio limits (loss/active/cancel/time) — maps ~1:1 to QUANTFLO risk-compliance. |
| 5 | Futures-multiplier Position/PnL accounting | `position/position.py`, `position_manager.py` | **ELITE** | Correct multiplier PnL incl. position-flip realized math. |
| 6 | CME futures instrument metadata | `examples/instrument_meta.yaml` | **ELITE (data)** | ES/NQ/MES/MNQ multipliers verified; seed for our instrument table (YM/MYM add manually). |
| 7 | IB native brokerage integration | `brokerage/ib_brokerage.py` (~1,580 ln) | **ELITE-conditional** | Battle-tested if we execute via IB; else structural reference only. |
| 8 | PyQt5 live monitor console | `quanttrader/gui/ui_*.py` (11 files) | **NOT-ELITE** | Desktop, IB-coupled; QUANTFLO monitoring is web/service-based. Concepts only. |

### Rejected / NOT-ELITE (with reason)
- `quanttrader/risk/margin_manager.py` — **empty stub** (`class MarginManager: pass`).
- `quanttrader/data/live_data_feed.py` — vestigial/broken (commented `quandl`, removed pandas `.ix`/`Adj. Close`).
- `quanttrader/portfolio_env.py`, `trading_env.py` — gym RL scaffolding; tangential.
- `examples/strategy/dual_*` — illustrative `on_tick` prints, no complete signal logic.
- PyQt5 GUI (#8) — desktop-bound.

## 4. Feasibility probe — **EXECUTED · PASS**

- **Command:** `python -m pytest tests/test_strats.py` (from `_research/quanttrader/`)
- **Data:** bundled `tests/test_data/TEST.csv` (no credentials, no network).
- **Env:** throwaway venv; `pip install pandas numpy pytz scipy scikit-learn matplotlib seaborn psutil pyyaml ta ibapi pyqt5` + `pip install -e . --no-deps`.
- **Result:** `1 passed in 2.21s`. `import quanttrader` succeeded (v0.5.5).
- **Proves:** the event-driven backtest engine (#3), backtest simulated brokerage
  fills/commission (#2), brokerage-abstraction backtest path (#1), and
  futures-multiplier position/PnL (#5) all run end-to-end offline. `df_trades` was
  non-empty as asserted.
- **Not probed (needs creds):** IB live path (#7) — requires TWS/Gateway + account.
  RiskManager full limits (#4) are only wired in the live GUI path; the backtest
  uses `PassThroughRiskManager`, so #4's limits are validated by reading, not run.

## 5. License-compatibility note

Permissive Apache-2.0 → **direct port allowed** (no clean-room needed). Recommended
target QUANTFLO modules: the brokerage abstraction → `execution/`; backtest sim
brokerage + engine → testers (Team 3) backtest module; futures-multiplier PnL →
`core` accounting; RiskManager interface → `teams/risk_compliance`; instrument
metadata → already seeded in `core/instruments`. Add a `NOTICE`/attribution entry
crediting Letian Wang for any ported code.
