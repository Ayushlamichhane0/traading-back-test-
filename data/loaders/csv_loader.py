"""CSV data loader."""
from __future__ import annotations

import pandas as pd

from config.schema import InstrumentConfig
from data.loaders.base import BaseDataLoader


class CSVDataLoader(BaseDataLoader):
    """Expected CSV: datetime index column + OHLCV columns."""

    def load(self, instrument: InstrumentConfig) -> pd.DataFrame:
        df = pd.read_csv(instrument.data_path, parse_dates=True, index_col=0)
        df = self._validate(df, instrument.symbol)
        df = self._filter_date_range(df, instrument)
        return df
