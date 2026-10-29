"""Gold Trend Following Strategy with EMA Crossover and Trend Filter.

Rules:
  - Fast EMA: 20
  - Slow EMA: 50
  - Trend Filter EMA: 200
  - ATR: 14

Entry Signals:
  - LONG : Fast EMA crosses above Slow EMA AND Close > 200 EMA
  - SHORT: Fast EMA crosses below Slow EMA AND Close < 200 EMA

Risk Management:
  - SL: 2x ATR from entry price
  - TP: 3R (3 * risk distance, i.e., 6x ATR)
  - Position sizing based on platform risk configuration
"""
from __future__ import annotations

import logging
from typing import ClassVar

import numpy as np

from strategy.base import BaseStrategy
from strategy.indicators import atr, ema

logger = logging.getLogger(__name__)


class GoldTrend(BaseStrategy):
    """Trend-following strategy for Gold on 15m (or any intraday) timeframe."""

    def _setup_indicators(self) -> None:
        fast_period = int(self.config.params.get("fast_period", 20))
        slow_period = int(self.config.params.get("slow_period", 50))
        trend_period = int(self.config.params.get("trend_period", 200))
        atr_period = int(self.config.stop_loss.atr_period if self.config.stop_loss else 14)

        self.indicators["fast_ema"] = self.I(
            ema, self.data.Close, fast_period, name=f"EMA_{fast_period}"
        )
        self.indicators["slow_ema"] = self.I(
            ema, self.data.Close, slow_period, name=f"EMA_{slow_period}"
        )
        self.indicators["trend_ema"] = self.I(
            ema, self.data.Close, trend_period, name=f"EMA_{trend_period}"
        )
        self.indicators["atr"] = self.I(
            atr, self.data.High, self.data.Low, self.data.Close, atr_period, name=f"ATR_{atr_period}"
        )

    def _entry_signal(self) -> bool:
        # Long/short logic is handled directly in next()
        return False

    def _exit_signal(self) -> bool:
        # Exits are managed via SL/TP brackets in next()
        return False

    def next(self) -> None:
        ts = self.data.index[-1]

        fast = self.indicators["fast_ema"]
        slow = self.indicators["slow_ema"]
        trend = self.indicators["trend_ema"]
        atr_arr = self.indicators["atr"]

        # Ensure warm-up bars have elapsed
        if len(fast) < 2 or len(slow) < 2 or len(trend) < 2 or len(atr_arr) < 1:
            return
        if np.isnan(fast[-1]) or np.isnan(slow[-1]) or np.isnan(trend[-1]) or np.isnan(atr_arr[-1]):
            return
        if np.isnan(fast[-2]) or np.isnan(slow[-2]):
            return

        # 1. Position management & optional early crossover exit
        if self.position:
            exit_on_cross = bool(self.config.params.get("exit_on_cross", False))
            if exit_on_cross:
                if self.position.is_long and (fast[-2] >= slow[-2] and fast[-1] < slow[-1]):
                    self.position.close()
                elif self.position.is_short and (fast[-2] <= slow[-2] and fast[-1] > slow[-1]):
                    self.position.close()
            return

        # 2. Session filter gate
        if self.session_filter is not None and not self.session_filter.is_active(ts):
            return

        # 3. ATR, SL and TP parameters
        close = float(self.data.Close[-1])
        atr_val = float(atr_arr[-1])
        if atr_val <= 0:
            return

        sl_mult = float(self.config.stop_loss.value if self.config.stop_loss else 2.0)
        tp_rr = float(self.config.take_profit.value if self.config.take_profit else 3.0)

        sl_dist = sl_mult * atr_val
        tp_dist = tp_rr * sl_dist

        crossed_up = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
        crossed_down = fast[-2] >= slow[-2] and fast[-1] < slow[-1]

        # 4. Long Entry: 20 crosses above 50 AND price is above 200 EMA
        if crossed_up and close > trend[-1]:
            sl = close - sl_dist
            tp = close + tp_dist
            size = self._size_for_sl(close, sl)
            if size >= 1:
                self.buy(size=size, sl=sl, tp=tp)
                logger.debug(
                    "BUY  %s %s size=%.1f entry=%.2f sl=%.2f tp=%.2f",
                    self.symbol, ts, size, close, sl, tp,
                )

        # 5. Short Entry: 20 crosses below 50 AND price is below 200 EMA
        elif crossed_down and close < trend[-1]:
            sl = close + sl_dist
            tp = close - tp_dist
            size = self._size_for_sl(close, sl)
            if size >= 1:
                self.sell(size=size, sl=sl, tp=tp)
                logger.debug(
                    "SELL %s %s size=%.1f entry=%.2f sl=%.2f tp=%.2f",
                    self.symbol, ts, size, close, sl, tp,
                )

    def _size_for_sl(self, entry: float, sl: float) -> float:
        """Calculate position size adhering to risk budget and account equity."""
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


# Alias for backward compatibility or alternate naming convention
GoldTrendStrategy = GoldTrend
