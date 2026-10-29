"""Pytest fixtures for trading platform test suite."""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config.schema import (
    ExecutionConfig,
    InstrumentConfig,
    PlatformConfig,
    RiskConfig,
    RiskType,
    SessionFilterConfig,
    SessionWindow,
    StopLossConfig,
    StrategyConfig,
    TakeProfitConfig,
    Timeframe,
)
from engine.trade_log import TRADE_LOG_COLUMNS


@pytest.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """Generate 200 bars of synthetic OHLCV data with UTC DatetimeIndex."""
    dates = pd.date_range("2024-01-01 00:00:00", periods=200, freq="1h", tz="UTC")
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.normal(0, 0.5, 200))
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    high = np.maximum(open_, close) + np.abs(np.random.normal(0, 0.2, 200))
    low = np.minimum(open_, close) - np.abs(np.random.normal(0, 0.2, 200))
    volume = np.random.randint(100, 1000, 200)

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
    df.index.name = "datetime"
    return df


@pytest.fixture
def sample_trades_df() -> pd.DataFrame:
    """Hand-crafted canonical trade log with pre-computed expected metrics:
    - 5 trades: 3 wins (100, 200, 300), 2 losses (-100, -200)
    - Net PnL: 300.0
    - Gross Profit: 600.0
    - Gross Loss: 300.0
    - Profit Factor: 2.0
    - Win Rate: 60.0%
    - Expectancy: 60.0
    - Max Consecutive Wins: 3
    - Max Consecutive Losses: 2
    """
    times = pd.date_range("2024-01-01 08:00:00", periods=5, freq="2h", tz="UTC")
    exit_times = [t + pd.Timedelta(hours=1) for t in times]

    data = {
        "symbol": ["EURUSD"] * 5,
        "strategy": ["MA Crossover"] * 5,
        "side": ["long", "long", "long", "short", "short"],
        "entry_time": times,
        "exit_time": exit_times,
        "entry_price": [1.1000, 1.1050, 1.1100, 1.1080, 1.1040],
        "exit_price": [1.1020, 1.1090, 1.1160, 1.1100, 1.1080],
        "size": [10000.0] * 5,
        "pnl": [100.0, 200.0, 300.0, -100.0, -200.0],
        "commission": [2.0] * 5,
        "r_multiple": [1.0, 2.0, 3.0, -1.0, -2.0],
        "session": ["London", "London", "New_York", "New_York", "Asia"],
        "duration_bars": [1] * 5,
        "duration_hours": [1.0] * 5,
        "day_of_week": ["Monday", "Monday", "Monday", "Monday", "Monday"],
        "hour_of_day": [8, 10, 12, 14, 16],
    }
    return pd.DataFrame(data, columns=TRADE_LOG_COLUMNS)


@pytest.fixture
def sample_equity_series() -> pd.Series:
    """Hand-crafted equity curve:
    100,000 -> 105,000 (peak) -> 95,000 (trough) -> 102,000
    - Peak: 105,000
    - Max Drawdown: 95,000 - 105,000 = -10,000
    - Max Drawdown Pct: -10,000 / 105,000 * 100 = -9.5238%
    """
    dates = pd.date_range("2024-01-01", periods=4, freq="1d", tz="UTC")
    return pd.Series([100000.0, 105000.0, 95000.0, 102000.0], index=dates, name="Equity")


@pytest.fixture
def sample_platform_config(tmp_path: Path, sample_ohlcv_df: pd.DataFrame) -> PlatformConfig:
    """Fixture providing a valid PlatformConfig pointing to temporary test CSV."""
    csv_file = tmp_path / "test_data.csv"
    sample_ohlcv_df.to_csv(csv_file)

    return PlatformConfig(
        instruments=[
            InstrumentConfig(
                symbol="TEST_SYM",
                timeframe=Timeframe.H1,
                data_path=csv_file,
                date_start=date(2024, 1, 1),
                date_end=date(2024, 1, 5),
            )
        ],
        risk=RiskConfig(type=RiskType.PERCENT, value=1.0, max_open_positions=1),
        execution=ExecutionConfig(
            initial_cash=100000.0,
            commission=0.0002,
            spread=0.0001,
            trade_on_close=False,
            exclusive_orders=True,
        ),
        session_filter=SessionFilterConfig(
            enabled=True,
            windows=[
                SessionWindow(name="London", start_utc=time(7, 0), end_utc=time(15, 0)),
            ],
        ),
        strategy=StrategyConfig(
            name="MA Crossover",
            module="strategy.ma_crossover.MACrossoverStrategy",
            params={"fast_period": 10, "slow_period": 20},
            stop_loss=StopLossConfig(method="atr", value=1.5, atr_period=14),
            take_profit=TakeProfitConfig(method="rr", value=2.0),
        ),
        output_dir=tmp_path / "output",
    )
