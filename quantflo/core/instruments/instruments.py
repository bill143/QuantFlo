"""CME/CBOT index-futures contract specifications for QUANTFLO's scope instruments.

This module is pure configuration / reference data — instrument definitions only,
no trading logic. Margins are intentionally placeholders (``None``): real initial
and maintenance margins are exchange/broker-sourced and wired in a later phase.

Scope instruments: NQ, MNQ, ES, MES, YM, MYM.

Sources: CME Group / CBOT contract specifications. Times are US Central Time
(``America/Chicago``), the exchange's local time, following the CME Globex
equity-index schedule. Treat the hard-coded schedule as a reference default; the
authoritative calendar (holidays, early closes) is a later-phase data feed.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Exchange(StrEnum):
    """Listing exchange for a contract."""

    CME = "CME"    # Chicago Mercantile Exchange (E-mini/Micro S&P 500, Nasdaq-100)
    CBOT = "CBOT"  # Chicago Board of Trade (E-mini/Micro Dow)


@dataclass(frozen=True, slots=True)
class TradingHours:
    """Exchange trading schedule, in the instrument's local timezone.

    Equity-index futures on CME Globex trade nearly 24x5 with a daily settlement
    halt. ETH = Electronic Trading Hours (Globex). RTH = Regular Trading Hours
    (the cash-session-aligned window used for session-based analytics).
    """

    timezone: str        # IANA tz, e.g. "America/Chicago"
    eth_open: str        # Globex (electronic) session open, local time
    eth_close: str       # Globex session close, local time
    rth_open: str        # Regular trading hours open, local time
    rth_close: str       # Regular trading hours close, local time
    daily_halt: str      # daily maintenance/settlement halt window
    intraday_pause: str  # equity-index intraday trading pause window


# CME Globex equity-index schedule (US Central Time). Shared by all six contracts.
_CME_EQUITY_INDEX_HOURS = TradingHours(
    timezone="America/Chicago",
    eth_open="17:00",              # Sun-Thu 17:00 CT (re)open for the next session
    eth_close="16:00",             # 16:00 CT the next day
    rth_open="08:30",              # 08:30 CT
    rth_close="15:15",             # 15:15 CT
    daily_halt="16:00-17:00",      # daily settlement/maintenance halt
    intraday_pause="15:15-15:30",  # equity-index trading pause
)


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    """A single futures contract specification (reference/config data only)."""

    symbol: str                       # CME product root, e.g. "ES"
    name: str
    exchange: Exchange
    tick_size: Decimal                # minimum price increment, in index points
    point_value: Decimal              # USD value of one full index point
    tick_value: Decimal               # USD value of one tick (tick_size * point_value)
    currency: str
    contract_months: tuple[str, ...]  # delivery months (single-letter CME codes)
    trading_hours: TradingHours
    is_micro: bool
    initial_margin_usd: Decimal | None = None      # placeholder — broker/exchange sourced
    maintenance_margin_usd: Decimal | None = None  # placeholder — broker/exchange sourced


# Quarterly cycle: Mar(H), Jun(M), Sep(U), Dec(Z) — standard for equity-index futures.
_QUARTERLY: tuple[str, ...] = ("H", "M", "U", "Z")


def _spec(
    symbol: str,
    name: str,
    exchange: Exchange,
    tick_size: str,
    point_value: str,
    *,
    is_micro: bool,
    contract_months: tuple[str, ...] = _QUARTERLY,
) -> InstrumentSpec:
    """Build an :class:`InstrumentSpec`, deriving tick value from size x point value."""
    tick = Decimal(tick_size)
    point = Decimal(point_value)
    return InstrumentSpec(
        symbol=symbol,
        name=name,
        exchange=exchange,
        tick_size=tick,
        point_value=point,
        tick_value=tick * point,
        currency="USD",
        contract_months=contract_months,
        trading_hours=_CME_EQUITY_INDEX_HOURS,
        is_micro=is_micro,
    )


INSTRUMENTS: dict[str, InstrumentSpec] = {
    "NQ": _spec("NQ", "E-mini Nasdaq-100", Exchange.CME, "0.25", "20", is_micro=False),
    "MNQ": _spec("MNQ", "Micro E-mini Nasdaq-100", Exchange.CME, "0.25", "2", is_micro=True),
    "ES": _spec("ES", "E-mini S&P 500", Exchange.CME, "0.25", "50", is_micro=False),
    "MES": _spec("MES", "Micro E-mini S&P 500", Exchange.CME, "0.25", "5", is_micro=True),
    "YM": _spec("YM", "E-mini Dow ($5)", Exchange.CBOT, "1", "5", is_micro=False),
    "MYM": _spec("MYM", "Micro E-mini Dow ($0.50)", Exchange.CBOT, "1", "0.50", is_micro=True),
}


def get_instrument(symbol: str) -> InstrumentSpec:
    """Return the spec for a scope symbol (case-insensitive). Raises ``KeyError`` if unknown."""
    try:
        return INSTRUMENTS[symbol.upper()]
    except KeyError as exc:
        raise KeyError(f"Unknown QUANTFLO instrument: {symbol!r}") from exc


def all_symbols() -> tuple[str, ...]:
    """All in-scope instrument symbols."""
    return tuple(INSTRUMENTS.keys())
