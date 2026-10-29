"""Drawdown analytics on equity series."""
from __future__ import annotations

import numpy as np
import pandas as pd


def drawdown_metrics(equity: pd.Series) -> dict[str, float | int]:
    """Compute maximum drawdown, drawdown percentage, and duration."""
    if equity is None or equity.empty:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "max_drawdown_duration_days": 0,
            "current_drawdown": 0.0,
        }

    eq = equity.astype(float)
    peak = eq.cummax()
    dd = eq - peak
    peak_safe = peak.replace(0, np.nan)
    dd_pct = (dd / peak_safe) * 100.0

    underwater = dd < 0
    # Longest consecutive stretch underwater
    groups = (~underwater).cumsum()
    durations = underwater.groupby(groups).sum()
    max_duration_bars = int(durations.max()) if len(durations) > 0 else 0

    max_dd = float(dd.min()) if not np.isnan(dd.min()) else 0.0
    max_dd_pct = float(dd_pct.min()) if not np.isnan(dd_pct.min()) else 0.0
    curr_dd = float(dd.iloc[-1]) if len(dd) > 0 else 0.0

    return {
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_duration_days": max_duration_bars,
        "current_drawdown": curr_dd,
    }
