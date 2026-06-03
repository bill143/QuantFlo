"""Continuous-futures roll engine for QUANTFLO's CME index futures.

CLEAN-ROOM reimplementation of the roll **behavior** (not the code) observed in
Lumiwealth/lumibot (GPL-3.0): the six index futures (ES, MES, NQ, MNQ, YM, MYM)
trade the quarterly Mar/Jun/Sep/Dec cycle (codes H/M/U/Z) and roll from the front
contract to the next a fixed number of CME trading days before the third-Friday
expiry. No lumibot source was read or copied during implementation; see
``docs/decisions/0004-roll-engine-clean-room.md``. CME holidays come from the
maintained ``pandas_market_calendars`` CME equity calendar.
"""
from __future__ import annotations

import functools
from datetime import date, timedelta
from typing import Any

import pandas_market_calendars as mcal

MONTH_CODES: dict[int, str] = {3: "H", 6: "M", 9: "U", 12: "Z"}
QUARTERLY_MONTHS: tuple[int, ...] = (3, 6, 9, 12)
DEFAULT_ROLL_OFFSET_BDAYS = 8


@functools.lru_cache(maxsize=1)
def _cme_calendar() -> Any:
    for name in ("CME_Equity", "CMEGlobex_EquityIndex", "CME"):
        try:
            return mcal.get_calendar(name)
        except Exception:
            continue
    raise RuntimeError("no CME calendar available in pandas_market_calendars")


def _trading_days_before(expiry: date, count_needed: int) -> list[date]:
    lookback = timedelta(days=count_needed * 2 + 21)
    idx = _cme_calendar().valid_days(
        start_date=(expiry - lookback).isoformat(), end_date=expiry.isoformat()
    )
    return [d.date() for d in idx if d.date() < expiry]


def third_friday(year: int, month: int) -> date:
    """The third Friday of the given month (standard CME index-futures expiry)."""
    first = date(year, month, 1)
    first_friday = first + timedelta(days=(4 - first.weekday()) % 7)
    return first_friday + timedelta(days=14)


def roll_date(year: int, month: int, offset_bdays: int = DEFAULT_ROLL_OFFSET_BDAYS) -> date:
    """Roll date = ``offset_bdays`` CME trading days before the third-Friday expiry."""
    expiry = third_friday(year, month)
    days = _trading_days_before(expiry, offset_bdays)
    if len(days) < offset_bdays:
        raise ValueError(f"not enough CME trading days before {expiry}")
    return days[-offset_bdays]


def contract_symbol(root: str, year: int, month: int) -> str:
    """CME contract code, e.g. ``('ES', 2024, 3) -> 'ESH24'``."""
    return f"{root}{MONTH_CODES[month]}{year % 100:02d}"


def active_contract(d: date, root: str, offset_bdays: int = DEFAULT_ROLL_OFFSET_BDAYS) -> str:
    """The front contract held on ``d`` (rolls ``offset_bdays`` trading days before expiry)."""
    year = d.year
    for _ in range(4):
        for month in QUARTERLY_MONTHS:
            if d < roll_date(year, month, offset_bdays):
                return contract_symbol(root, year, month)
        year += 1
    raise RuntimeError(f"could not resolve active contract for {d}")


def roll_schedule(
    start: date, end: date, root: str, offset_bdays: int = DEFAULT_ROLL_OFFSET_BDAYS
) -> list[tuple[date, str]]:
    """``(effective_date, contract)`` pairs where the active contract changes in [start, end]."""
    schedule: list[tuple[date, str]] = []
    prev: str | None = None
    d = start
    while d <= end:
        current = active_contract(d, root, offset_bdays)
        if current != prev:
            schedule.append((d, current))
            prev = current
        d += timedelta(days=1)
    return schedule
