"""Tests for the instrument reference data (config, not trading logic)."""
from __future__ import annotations

from decimal import Decimal

from quantflo.core.instruments import (
    INSTRUMENTS,
    Exchange,
    all_symbols,
    get_instrument,
)

SCOPE = {"NQ", "MNQ", "ES", "MES", "YM", "MYM"}

# Expected (tick_size, point_value, tick_value, exchange) per CME/CBOT specs.
EXPECTED = {
    "NQ": (Decimal("0.25"), Decimal("20"), Decimal("5.00"), Exchange.CME),
    "MNQ": (Decimal("0.25"), Decimal("2"), Decimal("0.50"), Exchange.CME),
    "ES": (Decimal("0.25"), Decimal("50"), Decimal("12.50"), Exchange.CME),
    "MES": (Decimal("0.25"), Decimal("5"), Decimal("1.25"), Exchange.CME),
    "YM": (Decimal("1"), Decimal("5"), Decimal("5"), Exchange.CBOT),
    "MYM": (Decimal("1"), Decimal("0.50"), Decimal("0.50"), Exchange.CBOT),
}


def test_exactly_the_six_scope_instruments() -> None:
    assert set(all_symbols()) == SCOPE
    assert set(INSTRUMENTS) == SCOPE


def test_contract_specs_match_exchange_reference() -> None:
    for symbol, (tick, point, tick_value, exchange) in EXPECTED.items():
        spec = get_instrument(symbol)
        assert spec.tick_size == tick
        assert spec.point_value == point
        assert spec.tick_value == tick_value
        assert spec.exchange is exchange


def test_tick_value_is_derived_consistently() -> None:
    for spec in INSTRUMENTS.values():
        assert spec.tick_value == spec.tick_size * spec.point_value


def test_micro_flag_and_currency() -> None:
    assert get_instrument("ES").is_micro is False
    assert get_instrument("MES").is_micro is True
    assert all(s.currency == "USD" for s in INSTRUMENTS.values())


def test_margins_are_placeholders_in_phase_0() -> None:
    for spec in INSTRUMENTS.values():
        assert spec.initial_margin_usd is None
        assert spec.maintenance_margin_usd is None


def test_lookup_is_case_insensitive_and_validates() -> None:
    assert get_instrument("es").symbol == "ES"
    try:
        get_instrument("AAPL")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected KeyError for out-of-scope symbol")
