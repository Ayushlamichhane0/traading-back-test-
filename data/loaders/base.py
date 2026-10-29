"""Data-loader abstraction. The engine depends only on BaseDataLoader."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from config.schema import InstrumentConfig

REQUIRED_COLUMNS = {"Open", "High", "Low", "Close"}


class BaseDataLoader(ABC):
    """Swap CSV -> Parquet -> API -> DB without touching the engine."""

    @abstractmethod
    def load(self, instrument: InstrumentConfig) -> pd.DataFrame:
        """Return an OHLCV DataFrame with a tz-aware UTC DatetimeIndex."""
        ...

    @staticmethod
    def _validate(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"{symbol}: missing required columns {missing}")
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index, utc=True)
            except Exception as e:
                raise TypeError(f"{symbol}: index must be convertible to DatetimeIndex: {e}") from e

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        if df.index.has_duplicates:
            raise ValueError(f"{symbol}: duplicate timestamps in data")

        if not df.index.is_monotonic_increasing:
            df = df.sort_index()

        return df.ffill().dropna(subset=list(REQUIRED_COLUMNS))

    @staticmethod
    def _filter_date_range(df: pd.DataFrame, instrument: InstrumentConfig) -> pd.DataFrame:
        """Filter DataFrame by instrument's date_start and date_end."""
        if instrument.date_start:
            start_ts = pd.Timestamp(instrument.date_start).tz_localize("UTC")
            df = df.loc[df.index >= start_ts]
        if instrument.date_end:
            # Include the entire end date up to the last microsecond
            end_ts = pd.Timestamp(instrument.date_end).tz_localize("UTC") + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
            df = df.loc[df.index <= end_ts]
        return df
