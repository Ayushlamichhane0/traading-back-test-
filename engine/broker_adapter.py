"""Broker adapter and execution configuration for backtesting.py.

Translates platform ExecutionConfig and Broker options into backtesting.py
execution parameters.
"""
from __future__ import annotations

from typing import Any

from backtesting import Backtest

from config.schema import ExecutionConfig


class BrokerAdapter:
    """Configures backtesting execution parameters from ExecutionConfig."""

    def __init__(self, execution_config: ExecutionConfig):
        self.config = execution_config

    def get_backtest_kwargs(self) -> dict[str, Any]:
        """Convert ExecutionConfig to Backtest kwargs."""
        return {
            "cash": self.config.initial_cash,
            "commission": self.config.commission,
            "spread": self.config.spread,
            "trade_on_close": self.config.trade_on_close,
            "exclusive_orders": self.config.exclusive_orders,
            "finalize_trades": True,
        }

    def create_backtest(self, data, strategy_cls) -> Backtest:
        """Instantiate a Backtest engine with configured broker settings."""
        kwargs = self.get_backtest_kwargs()
        return Backtest(data, strategy_cls, **kwargs)
