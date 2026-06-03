"""Feature-pipeline tests: ATR math + pipeline composition."""
from __future__ import annotations

import pandas as pd
import pytest

from quantflo.data.features import ATR, FeaturePipeline


def _constant_range_ohlc(n: int, hl: float) -> pd.DataFrame:
    # Constant-range bars with no gaps -> True Range == hl every bar -> ATR converges to hl.
    rows = [(100.0, 100.0 + hl, 100.0, 100.0 + hl / 2, 10) for _ in range(n)]
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"])


def test_atr_constant_range_converges() -> None:
    atr = ATR(period=14).compute(_constant_range_ohlc(50, hl=10.0))
    assert pd.isna(atr.iloc[0])  # warmup
    assert round(float(atr.iloc[-1]), 6) == 10.0
    assert (atr.dropna() > 0).all()


def test_atr_invalid_period() -> None:
    with pytest.raises(ValueError):
        ATR(period=0)


def test_feature_pipeline_columns() -> None:
    df = _constant_range_ohlc(30, hl=5.0)
    pipe = FeaturePipeline().add(ATR(14)).add(ATR(7))
    out = pipe.compute(df)
    assert list(out.columns) == ["atr_14", "atr_7"]
    assert len(out) == len(df)
    assert pipe.feature_names == ["atr_14", "atr_7"]
