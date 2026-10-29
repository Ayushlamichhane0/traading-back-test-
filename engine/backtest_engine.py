"""Orchestrates load -> configure -> run -> collect canonical trade log."""
from __future__ import annotations

import logging
from importlib import import_module
from typing import Any

import pandas as pd
from backtesting import Backtest

from config.schema import PlatformConfig
from data.loaders.base import BaseDataLoader
from engine.broker_adapter import BrokerAdapter
from engine.trade_log import build_trade_log

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Central engine orchestrating the backtest workflow across all instruments."""

    def __init__(self, config: PlatformConfig, loader: BaseDataLoader):
        self.config = config
        self.loader = loader
        self.broker_adapter = BrokerAdapter(config.execution)

    def _resolve_strategy(self) -> type:
        module_path, class_name = self.config.strategy.module.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)

    def run(self) -> tuple[pd.DataFrame, pd.Series]:
        StrategyClass = self._resolve_strategy()
        all_trades: list[pd.DataFrame] = []
        all_equity: list[pd.Series] = []

        for instrument in self.config.instruments:
            logger.info("Backtesting %s %s", instrument.symbol, instrument.timeframe.value)
            data = self.loader.load(instrument)

            ConfiguredStrategy = StrategyClass.configure(
                self.config.strategy,
                instrument.symbol,
                self.config,
            )

            bt = Backtest(
                data,
                ConfiguredStrategy,
                cash=self.config.execution.initial_cash,
                commission=self.config.execution.commission,
                spread=self.config.execution.spread,
                trade_on_close=self.config.execution.trade_on_close,
                exclusive_orders=self.config.execution.exclusive_orders,
                finalize_trades=True,
            )
            stats = bt.run()

            trades = build_trade_log(
                raw_trades=stats["_trades"],
                symbol=instrument.symbol,
                strategy_name=self.config.strategy.name,
                session_filter=self.config.session_filter,
            )
            all_trades.append(trades)
            all_equity.append(stats["_equity_curve"]["Equity"])

        trade_log = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

        if len(all_equity) == 1:
            equity_curve = all_equity[0]
        elif len(all_equity) > 1:
            # Combine equity across multiple symbols
            eq_df = pd.concat(all_equity, axis=1).ffill().bfill()
            equity_curve = eq_df.sum(axis=1)
        else:
            equity_curve = pd.Series(dtype=float)

        return trade_log, equity_curve
