"""Canonical trade-log schema — the only contract analytics depends on."""
from __future__ import annotations

import pandas as pd

from config.schema import SessionFilterConfig

TRADE_LOG_COLUMNS = [
    "symbol",
    "strategy",
    "side",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "size",
    "pnl",
    "commission",
    "r_multiple",
    "session",
    "duration_bars",
    "duration_hours",
    "day_of_week",
    "hour_of_day",
]


def build_trade_log(
    raw_trades: pd.DataFrame,
    symbol: str,
    strategy_name: str,
    session_filter: SessionFilterConfig,
) -> pd.DataFrame:
    """Normalize backtesting.py's trade output into the platform schema."""
    if raw_trades is None or raw_trades.empty:
        return pd.DataFrame(columns=TRADE_LOG_COLUMNS)

    df = raw_trades.copy()
    df["symbol"] = symbol
    df["strategy"] = strategy_name
    df["side"] = df["Size"].apply(lambda s: "long" if s > 0 else "short")
    df["entry_time"] = pd.to_datetime(df["EntryTime"], utc=True)
    df["exit_time"] = pd.to_datetime(df["ExitTime"], utc=True)
    df["entry_price"] = df["EntryPrice"].astype(float)
    df["exit_price"] = df["ExitPrice"].astype(float)
    df["size"] = df["Size"].abs().astype(float)
    df["pnl"] = df["PnL"].astype(float)
    df["commission"] = df.get("Commission", 0.0).astype(float)

    # R-multiple: PnL / initial risk. backtesting.py exposes SL when set.
    if "SL" in df.columns and not df["SL"].isna().all():
        risk_per_unit = (df["EntryPrice"] - df["SL"]).abs()
    else:
        risk_per_unit = pd.Series(0.0, index=df.index)

    risk_cash = (risk_per_unit * df["size"]).astype(float)
    valid_risk = risk_cash > 0
    df["r_multiple"] = 0.0
    df.loc[valid_risk, "r_multiple"] = df.loc[valid_risk, "pnl"] / risk_cash.loc[valid_risk]
    df["r_multiple"] = df["r_multiple"].astype(float).fillna(0.0)

    df["session"] = df["entry_time"].apply(session_filter.classify)
    df["day_of_week"] = df["entry_time"].dt.day_name()
    df["hour_of_day"] = df["entry_time"].dt.hour
    df["duration_hours"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 3600.0

    if "ExitBar" in df.columns and "EntryBar" in df.columns:
        df["duration_bars"] = (df["ExitBar"] - df["EntryBar"]).astype(int)
    else:
        df["duration_bars"] = df["duration_hours"].astype(int)

    return df[TRADE_LOG_COLUMNS]
