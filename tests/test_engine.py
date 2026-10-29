"""Unit and integration tests for engine, data loaders, and report builder."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from config.schema import PlatformConfig
from data.loaders.csv_loader import CSVDataLoader
from data.loaders.parquet_loader import ParquetDataLoader
from engine.backtest_engine import BacktestEngine
from engine.trade_log import TRADE_LOG_COLUMNS, build_trade_log
from reports.builder import ReportBuilder


def test_csv_loader_load(sample_platform_config: PlatformConfig):
    """Test CSV loader validates and returns tz-aware UTC DataFrame."""
    loader = CSVDataLoader()
    df = loader.load(sample_platform_config.instruments[0])

    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is not None
    assert str(df.index.tz) == "UTC"
    assert {"Open", "High", "Low", "Close"}.issubset(df.columns)


def test_parquet_loader_load(tmp_path: Path, sample_ohlcv_df: pd.DataFrame, sample_platform_config: PlatformConfig):
    """Test Parquet loader validates and returns DataFrame."""
    pq_path = tmp_path / "test_data.parquet"
    sample_ohlcv_df.to_parquet(pq_path)

    inst = sample_platform_config.instruments[0].model_copy(update={"data_path": pq_path})
    loader = ParquetDataLoader()
    df = loader.load(inst)

    assert isinstance(df.index, pd.DatetimeIndex)
    assert len(df) == len(sample_ohlcv_df)


def test_build_trade_log_schema(sample_platform_config: PlatformConfig):
    """Test that build_trade_log correctly normalizes raw backtesting trades."""
    raw_trades = pd.DataFrame({
        "Size": [100, -50],
        "EntryBar": [10, 30],
        "ExitBar": [20, 45],
        "EntryPrice": [1.1000, 1.1050],
        "ExitPrice": [1.1050, 1.1020],
        "SL": [1.0950, 1.1100],
        "TP": [1.1100, 1.0950],
        "PnL": [50.0, 15.0],
        "Commission": [0.5, 0.5],
        "EntryTime": pd.to_datetime(["2024-01-01 08:00:00", "2024-01-01 14:00:00"], utc=True),
        "ExitTime": pd.to_datetime(["2024-01-01 10:00:00", "2024-01-01 16:00:00"], utc=True),
    })

    log = build_trade_log(
        raw_trades=raw_trades,
        symbol="EURUSD",
        strategy_name="MA Crossover",
        session_filter=sample_platform_config.session_filter,
    )

    assert list(log.columns) == TRADE_LOG_COLUMNS
    assert len(log) == 2
    assert log["side"].tolist() == ["long", "short"]
    assert log["duration_bars"].tolist() == [10, 15]


def test_end_to_end_backtest_and_report_generation(sample_platform_config: PlatformConfig, tmp_path: Path):
    """Test orchestrator execution from config to report deliverables."""
    loader = CSVDataLoader()
    engine = BacktestEngine(sample_platform_config, loader=loader)
    trades, equity = engine.run()

    assert isinstance(trades, pd.DataFrame)
    assert isinstance(equity, pd.Series)

    # Verify ReportBuilder HTML and Excel deliverables
    builder = ReportBuilder(output_dir=tmp_path / "reports")
    from analytics.analyzer import PerformanceAnalyzer
    report = PerformanceAnalyzer(trades, equity).compute()

    html_path = builder.to_html(report, equity, filename="test_report.html")
    xlsx_path = builder.to_excel(report, trades, filename="test_report.xlsx")

    assert html_path.exists()
    assert html_path.stat().st_size > 0
    assert xlsx_path.exists()
    assert xlsx_path.stat().st_size > 0
