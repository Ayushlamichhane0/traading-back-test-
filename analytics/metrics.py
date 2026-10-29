"""Pure metric functions. No plotting, no I/O, no side effects."""
from __future__ import annotations

import numpy as np
import pandas as pd


def basic_metrics(trades: pd.DataFrame) -> dict[str, float | int]:
    """Compute foundational trade performance metrics."""
    if trades.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "net_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "risk_reward": 0.0,
            "avg_r_multiple": 0.0,
        }

    pnl = trades["pnl"].astype(float)
    wins = trades[pnl > 0]
    losses = trades[pnl < 0]
    be = trades[pnl == 0]
    gross_profit = float(wins["pnl"].sum())
    gross_loss = float(abs(losses["pnl"].sum()))

    n_trades = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)
    n_be = len(be)

    avg_win = float(wins["pnl"].mean()) if n_wins > 0 else 0.0
    avg_loss = float(losses["pnl"].mean()) if n_losses > 0 else 0.0
    risk_reward = (avg_win / abs(avg_loss)) if (n_wins > 0 and n_losses > 0 and avg_loss != 0) else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    avg_r_mult = float(trades["r_multiple"].astype(float).mean()) if "r_multiple" in trades.columns else 0.0

    return {
        "total_trades": n_trades,
        "wins": n_wins,
        "losses": n_losses,
        "breakeven": n_be,
        "win_rate": float((n_wins / n_trades) * 100) if n_trades > 0 else 0.0,
        "loss_rate": float((n_losses / n_trades) * 100) if n_trades > 0 else 0.0,
        "net_pnl": float(pnl.sum()),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy": float(pnl.mean()) if n_trades > 0 else 0.0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward": risk_reward,
        "avg_r_multiple": avg_r_mult,
    }


def streak_metrics(trades: pd.DataFrame) -> dict[str, int]:
    """Max consecutive wins and losses, in chronological order."""
    if trades.empty:
        return {"max_consecutive_wins": 0, "max_consecutive_losses": 0}

    sort_col = "exit_time" if "exit_time" in trades.columns else trades.index
    ordered = trades.sort_values(sort_col)["pnl"].apply(
        lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
    ).tolist()

    max_w = max_l = cur_w = cur_l = 0
    for v in ordered:
        if v == 1:
            cur_w += 1
            cur_l = 0
            max_w = max(max_w, cur_w)
        elif v == -1:
            cur_l += 1
            cur_w = 0
            max_l = max(max_l, cur_l)
        else:
            cur_w = cur_l = 0

    return {"max_consecutive_wins": max_w, "max_consecutive_losses": max_l}
