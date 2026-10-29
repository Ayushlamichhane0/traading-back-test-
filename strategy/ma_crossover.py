"""Simple MA crossover — proves the full pipeline end to end."""
from __future__ import annotations

import numpy as np

from strategy.base import BaseStrategy
from strategy.indicators import atr, sma


class MACrossoverStrategy(BaseStrategy):
    """Enter long when fast SMA crosses above slow SMA.
    Exit when fast SMA crosses below slow SMA.

    Params (from YAML):
      fast_period: int
      slow_period: int
    """

    def _setup_indicators(self) -> None:
        fast = int(self.config.params.get("fast_period", 20))
        slow = int(self.config.params.get("slow_period", 50))
        atr_period = int(self.config.stop_loss.atr_period)

        self.indicators["fast_ma"] = self.I(
            sma, self.data.Close, fast, name=f"SMA_{fast}"
        )
        self.indicators["slow_ma"] = self.I(
            sma, self.data.Close, slow, name=f"SMA_{slow}"
        )
        self.indicators["atr"] = self.I(
            atr, self.data.High, self.data.Low, self.data.Close, atr_period, name=f"ATR_{atr_period}"
        )

    def _entry_signal(self) -> bool:
        fast = self.indicators["fast_ma"]
        slow = self.indicators["slow_ma"]
        if len(fast) < 2 or len(slow) < 2:
            return False
        if np.isnan(fast[-1]) or np.isnan(slow[-1]) or np.isnan(fast[-2]) or np.isnan(slow[-2]):
            return False
        crossed_up = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
        return bool(crossed_up)

    def _exit_signal(self) -> bool:
        fast = self.indicators["fast_ma"]
        slow = self.indicators["slow_ma"]
        if len(fast) < 2 or len(slow) < 2:
            return False
        if np.isnan(fast[-1]) or np.isnan(slow[-1]) or np.isnan(fast[-2]) or np.isnan(slow[-2]):
            return False
        crossed_down = fast[-2] >= slow[-2] and fast[-1] < slow[-1]
        return bool(crossed_down)
