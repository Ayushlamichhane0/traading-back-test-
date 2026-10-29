"""Unit tests for analytics package (metrics, drawdown, breakdowns, analyzer)."""
from __future__ import annotations

import pandas as pd
import pytest

from analytics import (
    PerformanceAnalyzer,
    basic_metrics,
    day_of_week_breakdown,
    drawdown_metrics,
    hour_of_day_breakdown,
    monthly_breakdown,
    session_breakdown,
    streak_metrics,
    symbol_breakdown,
    trade_distribution,
)


def test_basic_metrics_known_values(sample_trades_df: pd.DataFrame):
    """Assert pure metric functions against pre-computed fixture values."""
    metrics = basic_metrics(sample_trades_df)

    assert metrics["total_trades"] == 5
    assert metrics["wins"] == 3
    assert metrics["losses"] == 2
    assert metrics["breakeven"] == 0
    assert metrics["win_rate"] == 60.0
    assert metrics["loss_rate"] == 40.0
    assert metrics["net_pnl"] == 300.0
    assert metrics["gross_profit"] == 600.0
    assert metrics["gross_loss"] == 300.0
    assert metrics["profit_factor"] == 2.0
    assert metrics["expectancy"] == 60.0
    assert metrics["avg_win"] == 200.0
    assert metrics["avg_loss"] == -150.0
    assert metrics["risk_reward"] == pytest.approx(200.0 / 150.0)


def test_streak_metrics_known_values(sample_trades_df: pd.DataFrame):
    """Assert consecutive streaks calculations."""
    streaks = streak_metrics(sample_trades_df)
    assert streaks["max_consecutive_wins"] == 3
    assert streaks["max_consecutive_losses"] == 2


def test_drawdown_metrics_known_values(sample_equity_series: pd.Series):
    """Assert drawdown calculations against pre-computed values."""
    dd = drawdown_metrics(sample_equity_series)

    assert dd["max_drawdown"] == -10000.0
    assert dd["max_drawdown_pct"] == pytest.approx(-9.5238, rel=1e-3)
    assert dd["current_drawdown"] == -3000.0


def test_breakdowns_return_dataframes(sample_trades_df: pd.DataFrame):
    """Verify all breakdown functions generate correct columns and non-empty rows."""
    m = monthly_breakdown(sample_trades_df)
    assert not m.empty
    assert "month" in m.columns
    assert "net_pnl" in m.columns

    d = day_of_week_breakdown(sample_trades_df)
    assert not d.empty
    assert "day_of_week" in d.columns

    h = hour_of_day_breakdown(sample_trades_df)
    assert not h.empty
    assert "hour_of_day" in h.columns

    s = session_breakdown(sample_trades_df)
    assert not s.empty
    assert "session" in s.columns

    sym = symbol_breakdown(sample_trades_df)
    assert not sym.empty
    assert "symbol" in sym.columns

    dist = trade_distribution(sample_trades_df, bins=5)
    assert not dist.empty
    assert "r_bucket" in dist.columns
    assert "count" in dist.columns


def test_empty_trade_handling():
    """Ensure analytics handle empty trades gracefully without raising exceptions."""
    empty_df = pd.DataFrame()
    empty_series = pd.Series(dtype=float)

    m = basic_metrics(empty_df)
    assert m["total_trades"] == 0
    assert m["profit_factor"] == 0.0

    st = streak_metrics(empty_df)
    assert st["max_consecutive_wins"] == 0

    dd = drawdown_metrics(empty_series)
    assert dd["max_drawdown"] == 0.0

    analyzer = PerformanceAnalyzer(empty_df, empty_series)
    report = analyzer.compute()
    assert report["total_trades"] == 0
    assert report["best_month"]["month"] == "N/A"
