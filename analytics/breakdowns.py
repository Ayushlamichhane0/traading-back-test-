"""Performance breakdown slices (monthly, DOW, hour, session, symbol, distribution)."""
from __future__ import annotations

import pandas as pd


def monthly_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by exit month."""
    cols = ["month", "trades", "net_pnl", "win_rate"]
    if trades.empty or "exit_time" not in trades.columns:
        return pd.DataFrame(columns=cols)

    t = trades.copy()
    t["month"] = t["exit_time"].dt.strftime("%Y-%m")
    return (
        t.groupby("month")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
        )
        .reset_index()
    )


def day_of_week_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by day of week."""
    cols = ["day_of_week", "trades", "net_pnl", "win_rate"]
    if trades.empty or "day_of_week" not in trades.columns:
        return pd.DataFrame(columns=cols)

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    res = (
        trades.groupby("day_of_week")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
        )
        .reindex(days_order)
        .dropna(how="all")
        .reset_index()
    )
    return res


def hour_of_day_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by hour of day (UTC)."""
    cols = ["hour_of_day", "trades", "net_pnl", "win_rate"]
    if trades.empty or "hour_of_day" not in trades.columns:
        return pd.DataFrame(columns=cols)

    return (
        trades.groupby("hour_of_day")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
        )
        .sort_index()
        .reset_index()
    )


def _calc_pf(s: pd.Series) -> float:
    pos = s[s > 0].sum()
    neg = abs(s[s < 0].sum())
    if neg > 0:
        return float(pos / neg)
    if pos > 0:
        return float("inf")
    return 0.0


def session_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by trading session."""
    cols = ["session", "trades", "net_pnl", "win_rate", "profit_factor"]
    if trades.empty or "session" not in trades.columns:
        return pd.DataFrame(columns=cols)

    return (
        trades.groupby("session")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
            profit_factor=("pnl", _calc_pf),
        )
        .sort_values("net_pnl", ascending=False)
        .reset_index()
    )


def symbol_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by symbol."""
    cols = ["symbol", "trades", "net_pnl", "win_rate"]
    if trades.empty or "symbol" not in trades.columns:
        return pd.DataFrame(columns=cols)

    return (
        trades.groupby("symbol")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
        )
        .sort_values("net_pnl", ascending=False)
        .reset_index()
    )


def strategy_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by strategy name."""
    cols = ["strategy", "trades", "net_pnl", "win_rate"]
    if trades.empty or "strategy" not in trades.columns:
        return pd.DataFrame(columns=cols)

    return (
        trades.groupby("strategy")
        .agg(
            trades=("pnl", "size"),
            net_pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: float((x > 0).mean() * 100)),
        )
        .sort_values("net_pnl", ascending=False)
        .reset_index()
    )


def trade_distribution(trades: pd.DataFrame, bins: int = 20) -> pd.DataFrame:
    """R-multiple distribution frequency."""
    cols = ["r_bucket", "count"]
    if trades.empty or "r_multiple" not in trades.columns:
        return pd.DataFrame(columns=cols)

    r = trades["r_multiple"].astype(float)
    if r.nunique() <= 1:
        val = float(r.iloc[0]) if len(r) > 0 else 0.0
        return pd.DataFrame({"r_bucket": [f"[{val:.2f}, {val:.2f}]"], "count": [len(r)]})

    try:
        cuts = pd.cut(r, bins=bins)
        dist = cuts.value_counts().sort_index().reset_index()
        dist.columns = cols
        dist["r_bucket"] = dist["r_bucket"].astype(str)
        return dist
    except Exception:
        return pd.DataFrame(columns=cols)
