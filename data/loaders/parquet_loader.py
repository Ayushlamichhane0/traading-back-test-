"""Parquet data loader."""
from __future__ import annotations

import pandas as pd

from config.schema import InstrumentConfig
from data.loaders.base import BaseDataLoader


class ParquetDataLoader(BaseDataLoader):
    """Expected Parquet: datetime index or column + OHLCV columns."""

    def load(self, instrument: InstrumentConfig) -> pd.DataFrame:
        df = pd.read_parquet(instrument.data_path)
        df = self._validate(df, instrument.symbol)
        df = self._filter_date_range(df, instrument)
        return df
