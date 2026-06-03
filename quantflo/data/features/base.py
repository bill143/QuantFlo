"""Feature-pipeline interface: derive series from bars (math, NOT trading decisions).

A ``Feature`` computes a numeric series from an OHLCV bar DataFrame. The
``FeaturePipeline`` runs a set of features and returns them as columns. Nothing
here makes a trading decision — features are inputs that later phases consume.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Feature(ABC):
    """A derived series computed from bars."""

    name: str

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series (aligned to ``df``'s index) of the derived value."""


class FeaturePipeline:
    """Run a registered set of features over a bar DataFrame."""

    def __init__(self, features: list[Feature] | None = None) -> None:
        self._features: list[Feature] = list(features or [])

    def add(self, feature: Feature) -> FeaturePipeline:
        self._features.append(feature)
        return self

    @property
    def feature_names(self) -> list[str]:
        return [f.name for f in self._features]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for feature in self._features:
            out[feature.name] = feature.compute(df)
        return out
