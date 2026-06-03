"""Versioned strategy/indicator framework (Phase 2).

A ``Strategy`` is **pure decision logic** over market data: it maps bars (and
optional features) to a **target position per bar** in {-1, 0, +1}. It emits
**signals, never orders** — strategies never touch execution. The backtest engine
consumes these signals; live execution is a later phase (the Phase-2 hard wall).

Point-in-time contract: the signal at bar *t* may use data up to and including
bar *t*, **never future bars**. The backtest engine additionally applies an
execution lag (act on the next bar) so a same-bar signal cannot peek.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any

import pandas as pd


class SignalType(IntEnum):
    """A target position direction. NOT an order."""

    SHORT = -1
    FLAT = 0
    LONG = 1


class Strategy(ABC):
    """Pure signal-generating strategy: bars/features -> target position in {-1,0,1}."""

    key: str  # logical strategy id, e.g. "ema_crossover"
    version: int  # registry version

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params: dict[str, Any] = {**self.default_params(), **(params or {})}

    @classmethod
    def default_params(cls) -> dict[str, Any]:
        return {}

    @abstractmethod
    def generate_signals(
        self, bars: pd.DataFrame, features: pd.DataFrame | None = None
    ) -> pd.Series:
        """Return a target-position Series (index = bar order, values in {-1, 0, +1}).

        MUST be point-in-time: the value at bar *t* uses only data up to bar *t*.
        Returns positions, **never** orders.
        """

    def describe(self) -> dict[str, Any]:
        """Serializable description (for the registry)."""
        return {"key": self.key, "version": self.version, "params": dict(self.params)}
