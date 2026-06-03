#!/usr/bin/env python
"""Validate the reference strategy on REAL Phase-1 bars across the six instruments (gate D).

For each instrument: register a created StrategyVersion (ema_crossover tuned for that
instrument), run the validation battery on the real 1h bars, persist metrics + verdict,
and print real OOS / walk-forward / Monte-Carlo numbers with the OOS window shown
distinct from the in-sample window. No execution — signals + backtests only.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quantflo.backtest.validation import ValidationConfig
from quantflo.core.instruments import all_symbols
from quantflo.data.db import dispose_engine, session_scope
from quantflo.strategies.models import StrategyMetric, StrategyVersion
from quantflo.teams.testers import Tester

TIMEFRAME = "1h"
TENANT = "local"


async def _ensure_version(strategy_key: str, version: int, instrument: str) -> int:
    async with session_scope() as session:
        stmt = (
            pg_insert(StrategyVersion)
            .values(
                tenant_id=TENANT, strategy_key=strategy_key, version=version,
                name=f"EMA Crossover [{instrument}]",
                source_lineage=f"reference strategy (original), tuned for {instrument} {TIMEFRAME}",
                license="Proprietary", license_provenance="original",
                provenance_sha="reference", status="created",
            )
            .on_conflict_do_update(
                index_elements=["tenant_id", "strategy_key", "version"],
                set_={"status": "created", "name": f"EMA Crossover [{instrument}]"},
            )
            .returning(StrategyVersion.id)
        )
        return (await session.execute(stmt)).scalar_one()


async def main() -> int:
    tester = Tester(tenant=TENANT, val_config=ValidationConfig())
    for idx, symbol in enumerate(all_symbols(), start=1):
        version_id = await _ensure_version("ema_crossover", idx, symbol)
        async with session_scope() as session:
            await session.execute(
                delete(StrategyMetric).where(StrategyMetric.strategy_version_id == version_id)
            )
        try:
            report = await tester.validate_version(version_id, symbol, TIMEFRAME)
        except ValueError as exc:
            print(f"\n=== {symbol} {TIMEFRAME} === SKIP: {exc}")
            continue
        oos = report.out_of_sample
        wf = [round(f.metrics.sharpe, 2) for f in report.walk_forward]
        mc = report.monte_carlo
        print(f"\n=== {symbol} {TIMEFRAME} (version {idx}) ===")
        print(f"  verdict      : {'VALIDATED (challenger)' if report.passed else 'REJECTED'}")
        print(f"  best params  : {report.best_params}")
        print(f"  IS  Sharpe   : {report.in_sample.sharpe:.3f} (trades {report.in_sample.trade_count})")
        print(
            f"  OOS Sharpe   : {oos.sharpe:.3f} | maxDD {oos.max_drawdown:.3f} | "
            f"trades {oos.trade_count} | PF {oos.profit_factor:.2f} | win {oos.win_rate:.2f}"
        )
        print(f"  walk-forward : fold Sharpes {wf}")
        print(
            f"  Monte Carlo  : prob(+)={mc.prob_positive_return:.2f} "
            f"p05={mc.sharpe_p05:.2f} p50={mc.sharpe_p50:.2f} p95={mc.sharpe_p95:.2f}"
        )
        print(f"  reason       : {report.reason}")

    print("\n=== REGISTRY: strategy_versions (status / champion / provenance) ===")
    async with session_scope() as session:
        versions = (
            await session.execute(
                select(StrategyVersion)
                .where(
                    StrategyVersion.tenant_id == TENANT,
                    StrategyVersion.strategy_key == "ema_crossover",
                )
                .order_by(StrategyVersion.version)
            )
        ).scalars().all()
        for v in versions:
            print(
                f"  v{v.version} {v.name:<22} status={v.status:<10} "
                f"champion={v.champion_status:<10} prov={v.license_provenance} params={v.parameters}"
            )
        print("\n=== REGISTRY: IS vs OOS windows (distinct) ===")
        for v in versions:
            metrics = (
                await session.execute(
                    select(StrategyMetric).where(
                        StrategyMetric.strategy_version_id == v.id,
                        StrategyMetric.evaluation_type.in_(("in_sample", "out_of_sample")),
                    )
                )
            ).scalars().all()
            by_type = {m.evaluation_type: m for m in metrics}
            in_m = by_type.get("in_sample")
            oos_m = by_type.get("out_of_sample")
            if in_m and oos_m:
                distinct = oos_m.window_start is not None and in_m.window_end is not None and (
                    oos_m.window_start > in_m.window_end
                )
                print(
                    f"  v{v.version} {in_m.instrument}: IS ends {in_m.window_end} | "
                    f"OOS starts {oos_m.window_start} -> distinct={distinct}"
                )
    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
