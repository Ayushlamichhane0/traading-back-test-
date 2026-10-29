"""The drop-in strategy contract.

Every strategy inherits session filtering, risk-based position sizing,
and SL/TP level computation. Subclasses implement ONLY the alpha logic.
"""
from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any, ClassVar

import numpy as np
from backtesting import Strategy

from config.schema import PlatformConfig, SessionFilterConfig, StrategyConfig

logger = logging.getLogger(__name__)


class IndicatorDict(dict):
    """Dictionary that binds indicators to strategy attributes.

    This ensures backtesting.py discovers and automatically slices the
    indicators on every bar iteration during Strategy.next().
    """

    def __init__(self, strategy: Strategy):
        super().__init__()
        self._strategy = strategy

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        setattr(self._strategy, key, value)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self._strategy, key):
            return getattr(self._strategy, key)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self._strategy, key):
            return getattr(self._strategy, key)
        return super().get(key, default)


class BaseStrategy(Strategy):
    """Base class for all platform strategies.

    Subclasses must implement:
      - _setup_indicators(): populate self.indicators dict via self.I(...)
      - _entry_signal() -> bool
      - _exit_signal()  -> bool

    The base class handles:
      - session filtering (no entries outside allowed windows)
      - risk-based position sizing
      - ATR / percentage / fixed-point SL and TP levels
    """

    # Injected by the engine before Backtest.run()
    config: ClassVar[StrategyConfig]
    symbol: ClassVar[str]
    session_filter: ClassVar[SessionFilterConfig | None] = None
    _platform_config: ClassVar[PlatformConfig]

    @classmethod
    def configure(
        cls,
        strategy_config: StrategyConfig,
        symbol: str,
        platform_config: PlatformConfig,
    ) -> type["BaseStrategy"]:
        """Return a dynamic subclass configured for the target instrument and run."""
        subclass = type(
            f"{cls.__name__}_{symbol}",
            (cls,),
            {
                "config": strategy_config,
                "symbol": symbol,
                "session_filter": platform_config.session_filter,
                "_platform_config": platform_config,
            },
        )
        return subclass

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def init(self) -> None:
        self.indicators: IndicatorDict = IndicatorDict(self)
        self._setup_indicators()

    @abstractmethod
    def _setup_indicators(self) -> None:
        """Populate self.indicators. Called once before the bar loop."""
        ...

    @abstractmethod
    def _entry_signal(self) -> bool:
        """Return True on the bar where a new entry should be opened."""
        ...

    @abstractmethod
    def _exit_signal(self) -> bool:
        """Return True on the bar where an open position should be closed."""
        ...

    # ------------------------------------------------------------------ #
    # Main bar loop
    # ------------------------------------------------------------------ #
    def next(self) -> None:
        ts = self.data.index[-1]

        # 1. Session gate: no new entries outside allowed windows.
        in_session = self.session_filter is None or self.session_filter.is_active(ts)

        if not self.position:
            if in_session and self._entry_signal():
                size = self._position_size()
                if size >= 1:
                    sl, tp = self._stop_levels()
                    self.buy(size=size, sl=sl, tp=tp)
                    logger.debug(
                        "ENTRY %s %s size=%.4f sl=%s tp=%s",
                        self.symbol, ts, size, sl, tp,
                    )
        else:
            if self._exit_signal():
                self.position.close()
                logger.debug("EXIT %s %s", self.symbol, ts)

    # ------------------------------------------------------------------ #
    # Risk: position sizing
    # ------------------------------------------------------------------ #
    def _position_size(self) -> float:
        """Convert risk budget into units, respecting cash and margin."""
        risk_cfg = self._platform_config.risk
        equity = self.equity
        entry_price = self.data.Close[-1]

        sl_price, _ = self._stop_levels()
        if sl_price is None or sl_price == entry_price:
            return 0.0

        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0:
            return 0.0

        if risk_cfg.type.value == "percent":
            risk_cash = equity * (risk_cfg.value / 100.0)
        else:
            risk_cash = risk_cfg.value

        units = risk_cash / sl_distance

        # Cap by available cash (no leverage assumed; margin configurable upstream)
        max_units_by_cash = equity / entry_price
        units = min(units, max_units_by_cash * 0.99)
        whole_units = int(np.floor(units))
        return float(max(whole_units, 0))

    # ------------------------------------------------------------------ #
    # Risk: SL / TP levels
    # ------------------------------------------------------------------ #
    def _stop_levels(self) -> tuple[float | None, float | None]:
        """Compute absolute SL and TP prices for a LONG entry.

        For SHORT entries the engine/strategy layer mirrors the distance.
        """
        entry = self.data.Close[-1]
        sl_cfg = self.config.stop_loss
        tp_cfg = self.config.take_profit

        # --- Stop loss ---
        if sl_cfg.method == "atr":
            atr_val = self.indicators.get("atr")
            if atr_val is None or len(atr_val) == 0 or np.isnan(atr_val[-1]):
                return None, None
            sl_dist = atr_val[-1] * sl_cfg.value
        elif sl_cfg.method == "fixed_pct":
            sl_dist = entry * (sl_cfg.value / 100.0)
        else:  # fixed_points
            sl_dist = sl_cfg.value

        sl_price = entry - sl_dist

        # --- Take profit ---
        tp_price = None
        if tp_cfg:
            if tp_cfg.method == "rr":
                tp_price = entry + sl_dist * tp_cfg.value
            elif tp_cfg.method == "fixed_pct":
                tp_price = entry + entry * (tp_cfg.value / 100.0)
            else:  # fixed_points
                tp_price = entry + tp_cfg.value

        return sl_price, tp_price
