"""Backtest bias detectors: lookahead-bias and recursive-formula bias.

CLEAN-ROOM reimplementations of freqtrade's (GPL-3.0) lookahead-analysis and
recursive-analysis BEHAVIOR — **no freqtrade source copied** (ADR 0005; provenance:
freqtrade source-probe ``✅ PASS @ 9eededca``). Both operate at the SIGNAL level on
the :class:`Strategy` interface, so they validate any candidate strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from quantflo.strategies.base import Strategy


@dataclass(frozen=True)
class BiasResult:
    """Outcome of a bias check."""

    has_bias: bool
    differing_signals: int
    detail: dict[str, Any]


def detect_lookahead_bias(strategy: Strategy, bars: pd.DataFrame, cutoff: int = 10) -> BiasResult:
    """Flag a strategy whose PAST signals change when FUTURE bars are removed.

    Signals on the common prefix must be identical whether or not later bars exist;
    if they differ, the strategy peeked forward (lookahead bias).
    """
    if cutoff < 1 or len(bars) <= cutoff + 2:
        raise ValueError("need more bars than the cutoff for lookahead analysis")
    full = strategy.generate_signals(bars).reset_index(drop=True)
    truncated = strategy.generate_signals(bars.iloc[:-cutoff]).reset_index(drop=True)
    overlap = len(truncated)
    differing = int((full.iloc[:overlap].to_numpy() != truncated.to_numpy()).sum())
    return BiasResult(
        has_bias=differing > 0,
        differing_signals=differing,
        detail={"cutoff": cutoff, "overlap": overlap},
    )


def detect_recursive_bias(
    strategy: Strategy,
    bars: pd.DataFrame,
    startups: tuple[int, ...] = (50, 500),
    compare_len: int = 60,
) -> BiasResult:
    """Flag a strategy whose recent signals depend on how many startup bars precede them.

    Compute the tail signals using short vs long startup windows ending on the SAME
    final bars; if they differ, an indicator is recursively unstable (non-converged,
    e.g. an EMA/RSI given too few startup candles).
    """
    ordered = tuple(sorted(startups))
    if len(bars) < ordered[-1] + compare_len:
        raise ValueError("not enough bars for recursive analysis")
    tails: list[Any] = []
    for startup in ordered:
        window = bars.iloc[len(bars) - (startup + compare_len) :].reset_index(drop=True)
        signals = strategy.generate_signals(window).reset_index(drop=True)
        tails.append(signals.iloc[-compare_len:].to_numpy())
    reference = tails[-1]
    max_diff = max((int((tail != reference).sum()) for tail in tails[:-1]), default=0)
    return BiasResult(
        has_bias=max_diff > 0,
        differing_signals=max_diff,
        detail={"startups": list(ordered), "compare_len": compare_len},
    )
