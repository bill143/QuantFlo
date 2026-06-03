"""Event-driven futures backtest engine (point-in-time correct).

Adapted (permissive — Apache-2.0) from quanttrader's event-driven backtest +
no-look-ahead DataBoard and simulated-brokerage fill/commission model, with
attribution recorded in the registry (provenance: quanttrader source-probe
``✅ PASS`` local ``tests/test_strats.py``; ADR 0006).

Point-in-time contract (no lookahead): the engine executes the position implied by
bar *t-1*'s signal at bar *t*'s OPEN — a one-bar execution lag, so a signal can
never act on the bar it was computed from. Positions are discrete full size
(signal in {-1, 0, +1} x ``contracts``). Per-contract roll handling: when the
continuous series changes contract, the position is rolled (close old at its last
close, reopen new at the next open) so a cross-contract price gap is never booked
as PnL. Signals only — this engine never sends an order anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quantflo.backtest.metrics import PerformanceMetrics, compute_metrics


@dataclass(frozen=True)
class BacktestConfig:
    """Contract economics + fill assumptions for a backtest."""

    point_value: float
    tick_size: float
    commission_per_contract: float = 2.5  # per side, per contract
    slippage_ticks: float = 1.0  # adverse fill, in ticks
    contracts: int = 1
    initial_capital: float = 100_000.0
    periods_per_year: float = 252.0


@dataclass(frozen=True)
class BacktestResult:
    """Outcome of a backtest run (real numbers, no orders)."""

    equity_curve: pd.Series
    returns: pd.Series
    trade_pnls: list[float]
    metrics: PerformanceMetrics
    final_equity: float
    total_commission: float


class Backtester:
    """Run a strategy's signals over a continuous bar series with realistic fills."""

    def __init__(self, config: BacktestConfig) -> None:
        self.cfg = config

    def run(self, bars: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        cfg = self.cfg
        n = len(bars)
        if n == 0 or len(signals) != n:
            raise ValueError("bars and signals must be non-empty and the same length")

        pv = cfg.point_value
        slip = cfg.slippage_ticks * cfg.tick_size
        comm = cfg.commission_per_contract
        opens = pd.to_numeric(bars["open"]).to_numpy(dtype=float)
        closes = pd.to_numeric(bars["close"]).to_numpy(dtype=float)
        contract_col = bars["contract"].to_numpy()
        times = pd.to_datetime(bars["time"].to_numpy(), utc=True)
        sig = signals.reset_index(drop=True).astype(int).to_numpy()

        state = _State(cash=cfg.initial_capital)
        trade_pnls: list[float] = []
        equity_points: list[float] = []

        def close_position(exit_price: float) -> None:
            side = -1 if state.pos > 0 else 1  # sell to close a long, buy to close a short
            fill = exit_price + side * slip
            gross = state.pos * (fill - state.entry) * pv
            close_comm = comm * abs(state.pos)
            state.cash += gross - close_comm
            state.commission_total += close_comm
            trade_pnls.append(gross - state.open_comm - close_comm)
            state.pos = 0
            state.entry = 0.0
            state.open_comm = 0.0

        def open_position(target: int, base_price: float) -> None:
            side = 1 if target > 0 else -1  # buy to open a long, sell to open a short
            fill = base_price + side * slip
            open_comm = comm * abs(target)
            state.cash -= open_comm
            state.commission_total += open_comm
            state.pos = target
            state.entry = fill
            state.open_comm = open_comm

        for i in range(n):
            # 1. Roll: close the old contract at its last close (no cross-contract gap PnL).
            if i >= 1 and contract_col[i] != contract_col[i - 1] and state.pos != 0:
                close_position(closes[i - 1])
            # 2. Execute the lag-1 target at this bar's open.
            target = int(sig[i - 1]) * cfg.contracts if i >= 1 else 0
            if target != state.pos:
                if state.pos != 0:
                    close_position(opens[i])
                if target != 0:
                    open_position(target, opens[i])
            # 3. Mark to market at the close.
            unrealized = state.pos * (closes[i] - state.entry) * pv if state.pos != 0 else 0.0
            equity_points.append(state.cash + unrealized)

        # Liquidate any residual position at the final close.
        if state.pos != 0:
            close_position(closes[n - 1])
            equity_points[-1] = state.cash

        equity = pd.Series(equity_points, index=times)
        returns = equity.pct_change(fill_method=None).fillna(0.0)
        years = max(n / cfg.periods_per_year, 1e-9)
        metrics = compute_metrics(returns, equity, trade_pnls, cfg.periods_per_year, years)
        return BacktestResult(
            equity_curve=equity,
            returns=returns,
            trade_pnls=trade_pnls,
            metrics=metrics,
            final_equity=float(equity.iloc[-1]),
            total_commission=state.commission_total,
        )


@dataclass
class _State:
    cash: float
    pos: int = 0
    entry: float = 0.0
    open_comm: float = 0.0
    commission_total: float = 0.0
