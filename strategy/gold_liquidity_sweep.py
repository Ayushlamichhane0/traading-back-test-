"""Gold Daily Liquidity Sweep — platform-integrated version.

Rules (identical to your standalone file):
  LONG  : 1m low  < PDL  AND  1m close > PDL  → BUY  at next bar open
  SHORT : 1m high > PDH  AND  1m close < PDH  → SELL at next bar open
  SL    : wick + buffer (below the sweep low / above the sweep high)
  TP    : opposite level (PDH for long, PDL for short)
  Filter: max N trades/day, max 1 per level, session gate

Reads all its settings from self.config.params (YAML `params:` block).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from strategy.base import BaseStrategy


@dataclass
class _Signal:
    side: str
    entry: float
    sl: float
    tp: float


# --------------------------------------------------------------------------- #
# Daily levels helper (your original code — unchanged)
# --------------------------------------------------------------------------- #
def add_daily_levels(df_1m: pd.DataFrame, day_shift_hours: int = 0) -> pd.DataFrame:
    df = df_1m.copy()
    df["_date"] = (df["time"] - pd.Timedelta(hours=day_shift_hours)).dt.date
    daily = (
        df.groupby("_date")
        .agg(_dh=("high", "max"), _dl=("low", "min"))
        .reset_index()
    )
    daily["pdh"] = daily["_dh"].shift(1)
    daily["pdl"] = daily["_dl"].shift(1)
    daily = daily[["_date", "pdh", "pdl"]]
    return df.drop(columns=["_dh", "_dl"], errors="ignore").merge(daily, on="_date", how="left")


class GoldLiquiditySweep(BaseStrategy):
    """Liquidity sweep of the previous day's high/low on 1-minute gold."""

    # ------------------------------------------------------------------ #
    # Indicators: compute PDH/PDL arrays aligned to the 1m index
    # ------------------------------------------------------------------ #
    def _setup_indicators(self) -> None:
        df = pd.DataFrame({
            "time": self.data.index,
            "high": self.data.High,
            "low": self.data.Low,
        })
        df = add_daily_levels(df, day_shift_hours=int(self.config.params.get("day_shift_hours", 0)))
        self._pdh_arr: np.ndarray = df["pdh"].to_numpy(dtype=float)
        self._pdl_arr: np.ndarray = df["pdl"].to_numpy(dtype=float)

        # Reset day state
        self._last_date = None
        self._day_state = {"PDH": False, "PDL": False, "count": 0}

    # ------------------------------------------------------------------ #
    # Exits: SL and TP handle everything (no signal-based exit)
    # ------------------------------------------------------------------ #
    def _entry_signal(self) -> bool:
        return False  # not used — overridden in next()

    def _exit_signal(self) -> bool:
        return False  # never used — SL/TP closes positions

    # ------------------------------------------------------------------ #
    # Main loop (overrides base so we can handle SHORT + day state)
    # ------------------------------------------------------------------ #
    def next(self) -> None:
        i = len(self.data) - 1
        ts = self.data.index[i]

        # ---- 1. reset per-day state ----
        today = ts.date()
        if today != self._last_date:
            self._last_date = today
            self._day_state = {"PDH": False, "PDL": False, "count": 0}

        # ---- 2. session gate (platform YAML filter) ----
        if self.session_filter is not None and not self.session_filter.is_active(ts):
            return

        # ---- 3. if a position is open, SL/TP will manage it ----
        if self.position:
            return

        # ---- 4. day trade limits ----
        max_per_day = int(self.config.params.get("max_trades_per_day", 2))
        if self._day_state["count"] >= max_per_day:
            return

        # ---- 5. daily levels ----
        pdh = self._pdh_arr[i]
        pdl = self._pdl_arr[i]
        if np.isnan(pdh) or np.isnan(pdl):
            return

        bar_low = self.data.Low[i]
        bar_high = self.data.High[i]
        bar_close = self.data.Close[i]

        pip = float(self.config.params.get("pip_size", 0.1))
        sl_buffer = float(self.config.params.get("sl_buffer_pips", 2.0)) * pip
        one_per_level = bool(self.config.params.get("one_per_level", True))

        # ---- 6. LONG: sell-side sweep ----
        if (not self._day_state["PDL"] or not one_per_level) and bar_low < pdl < bar_close:
            sl = bar_low - sl_buffer
            tp = pdh
            if sl < bar_close < tp:
                size = self._size_for_sl(bar_close, sl)
                if size >= 1:
                    self.buy(size=size, sl=sl, tp=tp)
                    self._day_state["PDL"] = True
                    self._day_state["count"] += 1
                    return

        # ---- 7. SHORT: buy-side sweep ----
        if (not self._day_state["PDH"] or not one_per_level) and bar_high > pdh > bar_close:
            sl = bar_high + sl_buffer
            tp = pdl
            if tp < bar_close < sl:
                size = self._size_for_sl(bar_close, sl)
                if size >= 1:
                    self.sell(size=size, sl=sl, tp=tp)
                    self._day_state["PDH"] = True
                    self._day_state["count"] += 1

    # ------------------------------------------------------------------ #
    # Risk sizing: same math as base class, but accepts entry & sl directly
    # (base class assumes LONG-only; we need direction-agnostic)
    # ------------------------------------------------------------------ #
    def _size_for_sl(self, entry: float, sl: float) -> float:
        risk_cfg = self._platform_config.risk
        equity = self.equity
        sl_dist = abs(entry - sl)
        if sl_dist <= 0:
            return 0.0

        if risk_cfg.type.value == "percent":
            risk_cash = equity * (risk_cfg.value / 100.0)
        else:
            risk_cash = risk_cfg.value

        units = risk_cash / sl_dist
        units = min(units, (equity / entry) * 0.99)
        whole_units = int(np.floor(units))
        return float(max(whole_units, 0))
