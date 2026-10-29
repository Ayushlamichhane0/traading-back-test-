"""Command-line interface for the trading platform.

Usage:
    source .venv/bin/activate && python cli.py run --config config/strategies/gold_liquidity_sweep.yaml
    # Or directly:
    ./.venv/bin/python3 cli.py run --config config/strategies/gold_liquidity_sweep.yaml
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from analytics.analyzer import PerformanceAnalyzer
from config.schema import PlatformConfig
from data.loaders.csv_loader import CSVDataLoader
from data.loaders.parquet_loader import ParquetDataLoader
from engine.backtest_engine import BacktestEngine
from logger import setup_logging
from reports.builder import ReportBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Trading Platform Backtest Engine")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--config", required=True, type=Path, help="Path to strategy YAML config")
    parser.add_argument(
        "--loader",
        choices=["csv", "parquet"],
        default="csv",
        help="Data loader type (default: csv)",
    )
    args = parser.parse_args()

    setup_logging(level=logging.INFO)
    cfg = PlatformConfig.from_yaml(args.config)

    loader = ParquetDataLoader() if args.loader == "parquet" else CSVDataLoader()
    engine = BacktestEngine(cfg, loader=loader)
    trades, equity = engine.run()

    analyzer = PerformanceAnalyzer(trades, equity)
    report = analyzer.compute()

    builder = ReportBuilder(cfg.output_dir)
    filename_prefix = cfg.strategy.name.lower().replace(" ", "_")
    html_path = builder.to_html(report, equity, filename=f"{filename_prefix}_report.html")
    xlsx_path = builder.to_excel(report, trades, filename=f"{filename_prefix}_report.xlsx")

    print("\n" + "=" * 46)
    print("       BACKTEST PERFORMANCE SUMMARY           ")
    print("=" * 46)
    print(f"Strategy     : {cfg.strategy.name}")
    print(f"HTML report  : {html_path}")
    print(f"Excel report : {xlsx_path}")
    print("-" * 46)
    print(f"Total Trades : {report['total_trades']}")
    print(f"Net PnL      : ${report['net_pnl']:,.2f}")
    print(f"Win Rate     : {report['win_rate']:.1f}%")
    pf_str = "inf" if report['profit_factor'] == float('inf') else f"{report['profit_factor']:.2f}"
    print(f"Profit Factor: {pf_str}")
    print(f"Expectancy   : ${report['expectancy']:.2f}")
    print(f"Max DD       : {report['max_drawdown_pct']:.2f}%")
    print("=" * 46 + "\n")


if __name__ == "__main__":
    main()
