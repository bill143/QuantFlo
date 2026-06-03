"""Team 3 (Testers): run the validation battery on real bars and persist verdicts.

Loads a created ``StrategyVersion``, resolves its ``Strategy`` class + parameter grid,
runs the full validation battery (in-sample / out-of-sample / walk-forward / Monte
Carlo) on the REAL bars, writes every metric to ``strategy_metrics`` (tagged by
instrument + window), and promotes the version to ``validated`` (a challenger) or
``rejected`` (with reason). No execution — signals + backtests only.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select, update

from quantflo.backtest.data import load_continuous_bars
from quantflo.backtest.engine import BacktestConfig
from quantflo.backtest.metrics import PerformanceMetrics
from quantflo.backtest.validation import ValidationConfig, ValidationReport, validate
from quantflo.core.instruments import get_instrument
from quantflo.data.db import session_scope
from quantflo.strategies.base import Strategy
from quantflo.strategies.library import EmaCrossover
from quantflo.strategies.models import StrategyMetric, StrategyVersion

# timeframe -> approx periods per year (CME index futures trade ~23h/day x 252 days).
_PERIODS_PER_YEAR: dict[str, float] = {
    "1d": 252.0,
    "1h": 252.0 * 23.0,
    "1m": 252.0 * 23.0 * 60.0,
}

_EMA_GRID: list[dict[str, Any]] = [
    {"fast": f, "slow": s} for f in (5, 8, 13, 21) for s in (34, 55, 89) if f < s
]

# strategy_key -> (Strategy class, default parameter grid)
STRATEGY_REGISTRY: dict[str, tuple[type[Strategy], list[dict[str, Any]]]] = {
    "ema_crossover": (EmaCrossover, _EMA_GRID),
}

_MIN_BARS = 200


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _ts(value: Any) -> datetime:
    converted: datetime = pd.Timestamp(value).to_pydatetime()
    return converted


class Tester:
    """Validate registry strategy versions against real bars; persist the verdict."""

    def __init__(self, tenant: str = "local", val_config: ValidationConfig | None = None) -> None:
        self._tenant = tenant
        self._cfg = val_config or ValidationConfig()

    def _bt_config(self, instrument: str, timeframe: str) -> BacktestConfig:
        spec = get_instrument(instrument)
        return BacktestConfig(
            point_value=float(spec.point_value),
            tick_size=float(spec.tick_size),
            commission_per_contract=2.5,
            slippage_ticks=1.0,
            contracts=1,
            periods_per_year=_PERIODS_PER_YEAR.get(timeframe, 252.0),
        )

    async def validate_version(
        self, version_id: int, instrument: str, timeframe: str
    ) -> ValidationReport:
        async with session_scope() as session:
            version = (
                await session.execute(
                    select(StrategyVersion).where(StrategyVersion.id == version_id)
                )
            ).scalar_one()
            strategy_key = version.strategy_key
        if strategy_key not in STRATEGY_REGISTRY:
            raise ValueError(f"no strategy class registered for '{strategy_key}'")
        strategy_cls, grid = STRATEGY_REGISTRY[strategy_key]

        bars = await load_continuous_bars(instrument, timeframe, self._tenant)
        if len(bars) < _MIN_BARS:
            await self._set_status(
                version_id, "rejected", f"insufficient bars ({len(bars)} < {_MIN_BARS})", {}
            )
            raise ValueError(f"insufficient bars ({len(bars)}) for {instrument}/{timeframe}")

        report = validate(strategy_cls, bars, grid, self._bt_config(instrument, timeframe),
                          self._cfg, instrument=instrument)
        await self._persist(version_id, instrument, report, bars)
        return report

    def _metric_row(
        self,
        version_id: int,
        instrument: str,
        evaluation_type: str,
        m: PerformanceMetrics,
        window: tuple[datetime, datetime] | None,
        extra: dict[str, Any] | None = None,
    ) -> StrategyMetric:
        return StrategyMetric(
            tenant_id=self._tenant,
            strategy_version_id=version_id,
            evaluation_type=evaluation_type,
            instrument=instrument,
            window_start=window[0] if window else None,
            window_end=window[1] if window else None,
            sharpe=m.sharpe,
            sortino=m.sortino,
            max_drawdown=m.max_drawdown,
            profit_factor=_finite(m.profit_factor),
            win_rate=m.win_rate,
            avg_trade=m.avg_trade,
            total_return=m.total_return,
            trade_count=m.trade_count,
            detail=extra or {},
        )

    async def _persist(
        self, version_id: int, instrument: str, report: ValidationReport, bars: pd.DataFrame
    ) -> None:
        cut = int(len(bars) * (1.0 - self._cfg.oos_fraction))
        is_window = (_ts(bars["time"].iloc[0]), _ts(bars["time"].iloc[cut - 1]))
        oos_window = (_ts(bars["time"].iloc[cut]), _ts(bars["time"].iloc[-1]))
        async with session_scope() as session:
            session.add(self._metric_row(version_id, instrument, "in_sample", report.in_sample, is_window))
            session.add(
                self._metric_row(version_id, instrument, "out_of_sample", report.out_of_sample, oos_window)
            )
            for fold in report.walk_forward:
                session.add(
                    self._metric_row(
                        version_id, instrument, "walk_forward", fold.metrics, None,
                        extra={"fold": fold.fold, "params": fold.params},
                    )
                )
            session.add(
                StrategyMetric(
                    tenant_id=self._tenant,
                    strategy_version_id=version_id,
                    evaluation_type="monte_carlo",
                    instrument=instrument,
                    sharpe=report.monte_carlo.sharpe_p50,
                    detail={
                        "runs": report.monte_carlo.runs,
                        "sharpe_p05": report.monte_carlo.sharpe_p05,
                        "sharpe_p95": report.monte_carlo.sharpe_p95,
                        "prob_positive_return": report.monte_carlo.prob_positive_return,
                    },
                )
            )
            status = "validated" if report.passed else "rejected"
            await session.execute(
                update(StrategyVersion)
                .where(StrategyVersion.id == version_id)
                .values(
                    status=status,
                    rejection_reason=None if report.passed else report.reason,
                    champion_status="challenger" if report.passed else "none",
                    parameters=report.best_params,
                )
            )

    async def _set_status(
        self, version_id: int, status: str, reason: str, params: dict[str, Any]
    ) -> None:
        async with session_scope() as session:
            await session.execute(
                update(StrategyVersion)
                .where(StrategyVersion.id == version_id)
                .values(status=status, rejection_reason=reason, parameters=params)
            )
