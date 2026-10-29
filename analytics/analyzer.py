"""PerformanceAnalyzer facade composing metrics, drawdowns, and breakdowns."""
from __future__ import annotations

from typing import Any

import pandas as pd

from analytics import breakdowns, drawdown, metrics


class PerformanceAnalyzer:
    """Compute every metric and breakdown required by the report."""

    def __init__(self, trades: pd.DataFrame, equity_curve: pd.Series):
        self.trades = trades if trades is not None else pd.DataFrame()
        self.equity = equity_curve if equity_curve is not None else pd.Series(dtype=float)

    def compute(self) -> dict[str, Any]:
        """Compute the full analytics suite."""
        result: dict[str, Any] = {}
        result.update(metrics.basic_metrics(self.trades))
        result.update(metrics.streak_metrics(self.trades))
        result.update(drawdown.drawdown_metrics(self.equity))

        result["monthly"] = breakdowns.monthly_breakdown(self.trades)
        result["day_of_week"] = breakdowns.day_of_week_breakdown(self.trades)
        result["hour_of_day"] = breakdowns.hour_of_day_breakdown(self.trades)
        result["session"] = breakdowns.session_breakdown(self.trades)
        result["symbol"] = breakdowns.symbol_breakdown(self.trades)
        result["strategy"] = breakdowns.strategy_breakdown(self.trades)
        result["distribution"] = breakdowns.trade_distribution(self.trades)

        # Highlight best / worst months
        if not result["monthly"].empty:
            m = result["monthly"]
            result["best_month"] = m.loc[m["net_pnl"].idxmax()].to_dict()
            result["worst_month"] = m.loc[m["net_pnl"].idxmin()].to_dict()
        else:
            result["best_month"] = {"month": "N/A", "net_pnl": 0.0, "trades": 0, "win_rate": 0.0}
            result["worst_month"] = {"month": "N/A", "net_pnl": 0.0, "trades": 0, "win_rate": 0.0}

        # Highlight best / worst sessions
        if not result["session"].empty:
            s = result["session"]
            result["best_session"] = s.iloc[0].to_dict()
            result["worst_session"] = s.iloc[-1].to_dict()
        else:
            result["best_session"] = {"session": "N/A", "net_pnl": 0.0, "trades": 0, "win_rate": 0.0}
            result["worst_session"] = {"session": "N/A", "net_pnl": 0.0, "trades": 0, "win_rate": 0.0}

        return result
