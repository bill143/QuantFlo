"""Roll-engine tests: third-Friday expiries, roll dates, active contract, schedule (gate C)."""
from __future__ import annotations

from datetime import date

import pytest

from quantflo.data import roll


@pytest.mark.parametrize(
    ("year", "month", "expected"),
    [
        (2024, 3, date(2024, 3, 15)),
        (2024, 6, date(2024, 6, 21)),
        (2024, 9, date(2024, 9, 20)),
        (2024, 12, date(2024, 12, 20)),
        (2023, 12, date(2023, 12, 15)),
        (2025, 3, date(2025, 3, 21)),
    ],
)
def test_third_friday(year: int, month: int, expected: date) -> None:
    assert roll.third_friday(year, month) == expected


def test_roll_date_is_8_trading_days_before_expiry() -> None:
    # 8 CME trading days before 2024-03-15 (3rd Friday) is 2024-03-05.
    assert roll.roll_date(2024, 3, 8) == date(2024, 3, 5)
    assert roll.roll_date(2024, 3, 8) < roll.third_friday(2024, 3)


def test_contract_symbol() -> None:
    assert roll.contract_symbol("ES", 2024, 3) == "ESH24"
    assert roll.contract_symbol("MNQ", 2025, 12) == "MNQZ25"


def test_active_contract_transitions_at_roll() -> None:
    assert roll.active_contract(date(2024, 1, 10), "ES") == "ESH24"
    assert roll.active_contract(date(2024, 3, 4), "ES") == "ESH24"  # day before roll
    assert roll.active_contract(date(2024, 3, 5), "ES") == "ESM24"  # roll day
    assert roll.active_contract(date(2024, 12, 31), "ES") == "ESH25"  # rolled to next year


def test_roll_schedule_2024_es() -> None:
    sched = roll.roll_schedule(date(2024, 1, 1), date(2024, 12, 31), "ES")
    assert sched == [
        (date(2024, 1, 1), "ESH24"),
        (date(2024, 3, 5), "ESM24"),
        (date(2024, 6, 11), "ESU24"),
        (date(2024, 9, 10), "ESZ24"),
        (date(2024, 12, 10), "ESH25"),
    ]
