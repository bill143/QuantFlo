"""Data-quality gate tests with deliberately malformed bars."""
from __future__ import annotations

from typing import Any

import pandas as pd

from quantflo.data.quality import (
    check_duplicates,
    check_gaps,
    check_ohlc_integrity,
    check_outliers,
    run_quality_checks,
)

_COLS = ["time", "open", "high", "low", "close", "volume"]


def _bars(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=_COLS)


def test_ohlc_integrity_flags_bad_bars() -> None:
    df = _bars([
        (pd.Timestamp("2024-01-02 14:30", tz="UTC"), 100, 101, 99, 100, 10),  # ok
        (pd.Timestamp("2024-01-02 14:31", tz="UTC"), 100, 98, 99, 100, 10),  # high<low
        (pd.Timestamp("2024-01-02 14:32", tz="UTC"), 100, 101, 99, 105, 10),  # close>high
    ])
    events = check_ohlc_integrity(df)
    assert len(events) == 2
    assert {e.event_type for e in events} == {"ohlc_integrity"}


def test_duplicates_detected() -> None:
    ts = pd.Timestamp("2024-01-02 14:30", tz="UTC")
    df = _bars([(ts, 100, 101, 99, 100, 10), (ts, 100, 101, 99, 100, 10)])
    events = check_duplicates(df)
    assert len(events) == 1 and events[0].event_type == "duplicate"


def test_intraday_gap_detected() -> None:
    df = _bars([
        (pd.Timestamp("2024-01-02 14:30", tz="UTC"), 100, 101, 99, 100, 10),
        (pd.Timestamp("2024-01-02 14:31", tz="UTC"), 100, 101, 99, 100, 10),
        (pd.Timestamp("2024-01-02 14:40", tz="UTC"), 100, 101, 99, 100, 10),  # 9-min gap
    ])
    events = check_gaps(df, "1m")
    assert len(events) == 1 and events[0].event_type == "gap"
    assert events[0].detail["missing_bars"] == 8


def test_outlier_detected() -> None:
    closes = [100.0 if i % 2 == 0 else 100.5 for i in range(40)]
    closes[20] = 500.0  # a price spike -> robust z-score blows past the threshold
    times = [
        pd.Timestamp("2024-01-02 14:30", tz="UTC") + pd.Timedelta(minutes=i) for i in range(40)
    ]
    df = _bars([(t, c, c, c, c, 10) for t, c in zip(times, closes, strict=True)])
    events = check_outliers(df, z_threshold=10.0)
    assert any(e.event_type == "outlier" for e in events)


def test_run_quality_checks_aggregates() -> None:
    df = _bars([(pd.Timestamp("2024-01-02 14:30", tz="UTC"), 100, 98, 99, 100, 10)])  # high<low
    assert any(e.event_type == "ohlc_integrity" for e in run_quality_checks(df, "1m"))
