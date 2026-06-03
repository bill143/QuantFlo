"""Market-data quality gates for QUANTFLO ingestion.

Pure detectors over a bar DataFrame (columns: ``time, open, high, low, close,
volume``). Each returns :class:`QualityEvent` records; the ingestion layer persists
them to ``data_quality_events`` and **never silently drops** bad data. No trading
logic — these are integrity checks on raw market data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

# Expected bar interval per timeframe code (seconds).
_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# CME index-futures RTH (regular trading hours), US Central time.
_RTH_OPEN = (8, 30)
_RTH_CLOSE = (15, 15)
_CT = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class QualityEvent:
    """A single data-quality finding."""

    event_type: str  # ohlc_integrity | duplicate | gap | outlier | session
    severity: str  # warning | error
    bar_time: Any  # pd.Timestamp | None
    detail: dict[str, Any]


def _to_ct(ts: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(_CT)


def is_rth(ts: pd.Timestamp) -> bool:
    """True if the bar falls in CME index RTH (08:30-15:15 CT), Mon-Fri."""
    local = _to_ct(ts)
    if local.weekday() >= 5:
        return False
    minutes = int(local.hour) * 60 + int(local.minute)
    return _RTH_OPEN[0] * 60 + _RTH_OPEN[1] <= minutes < _RTH_CLOSE[0] * 60 + _RTH_CLOSE[1]


def check_ohlc_integrity(df: pd.DataFrame) -> list[QualityEvent]:
    events: list[QualityEvent] = []
    for row in df.itertuples(index=False):
        op, hi, lo, cl = float(row.open), float(row.high), float(row.low), float(row.close)
        problems: list[str] = []
        if hi < lo:
            problems.append("high<low")
        if not (lo <= op <= hi):
            problems.append("open_out_of_range")
        if not (lo <= cl <= hi):
            problems.append("close_out_of_range")
        if min(op, hi, lo, cl) <= 0:
            problems.append("non_positive_price")
        if problems:
            events.append(
                QualityEvent("ohlc_integrity", "error", row.time, {"problems": problems})
            )
    return events


def check_duplicates(df: pd.DataFrame) -> list[QualityEvent]:
    events: list[QualityEvent] = []
    for ts in df.loc[df.duplicated(subset=["time"], keep="first"), "time"]:
        events.append(QualityEvent("duplicate", "error", ts, {"timestamp": str(ts)}))
    return events


def check_gaps(df: pd.DataFrame, timeframe: str) -> list[QualityEvent]:
    events: list[QualityEvent] = []
    interval = _INTERVAL_SECONDS.get(timeframe)
    if interval is None or len(df) < 2:
        return events
    times = pd.to_datetime(df["time"]).sort_values().reset_index(drop=True)
    expected = pd.Timedelta(seconds=interval)
    for i in range(1, len(times)):
        delta = times[i] - times[i - 1]
        if timeframe == "1d":
            if delta > pd.Timedelta(days=4):  # longer than a long weekend
                events.append(
                    QualityEvent(
                        "gap", "warning", times[i],
                        {"from": str(times[i - 1]), "to": str(times[i]), "delta_days": delta.days},
                    )
                )
        elif delta > expected * 1.5 and times[i].date() == times[i - 1].date():
            events.append(
                QualityEvent(
                    "gap", "warning", times[i],
                    {"from": str(times[i - 1]), "to": str(times[i]),
                     "missing_bars": int(delta / expected) - 1},
                )
            )
    return events


def check_outliers(df: pd.DataFrame, z_threshold: float = 10.0) -> list[QualityEvent]:
    """Flag bad ticks via a robust modified z-score (median/MAD) on close-to-close returns.

    MAD is used (not stddev) so a single spike cannot inflate the scale and mask itself.
    """
    events: list[QualityEvent] = []
    if len(df) < 20:
        return events
    close = pd.to_numeric(df["close"], errors="coerce")
    returns = close.pct_change(fill_method=None).dropna()
    if len(returns) < 10:
        return events
    median = returns.median()
    mad = (returns - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return events
    modified_z = 0.6745 * (returns - median) / mad
    for idx, mz in modified_z.items():
        if pd.notna(mz) and abs(mz) > z_threshold:
            events.append(
                QualityEvent(
                    "outlier", "warning", df.loc[idx, "time"],
                    {"return": float(returns.loc[idx]), "modified_zscore": float(mz)},
                )
            )
    return events


def check_sessions(df: pd.DataFrame) -> list[QualityEvent]:
    """Flag bars during the 16:00-17:00 CT daily maintenance halt (should not exist)."""
    events: list[QualityEvent] = []
    for row in df.itertuples(index=False):
        local = _to_ct(pd.Timestamp(row.time))
        if local.hour == 16:
            events.append(
                QualityEvent(
                    "session", "warning", row.time,
                    {"local_time": local.isoformat(), "note": "bar during 16:00-17:00 CT halt"},
                )
            )
    return events


def run_quality_checks(df: pd.DataFrame, timeframe: str) -> list[QualityEvent]:
    """Run every quality gate over ``df`` and return all findings."""
    return (
        check_ohlc_integrity(df)
        + check_duplicates(df)
        + check_gaps(df, timeframe)
        + check_outliers(df)
        + check_sessions(df)
    )
