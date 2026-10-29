# Trading Platform Backtest Engine

A Python-based framework for backtesting trading strategies on historical OHLCV data. Configure instruments, strategy parameters, risk limits, execution costs, and trading sessions in YAML; the command-line runner produces performance analytics and HTML/Excel reports.

> This is a backtesting and research tool. It does not connect to a broker or place live trades. Results on historical or synthetic data do not guarantee future performance.

## Features

- YAML configuration validated with Pydantic before each run.
- CSV and Parquet historical-data loaders.
- Multiple instruments and configurable date ranges.
- Risk-based position sizing, commission, spread, and session filtering.
- Built-in moving-average crossover, gold trend, and gold liquidity-sweep strategies.
- Trade, equity, drawdown, and performance breakdown analytics.
- HTML reports with charts and Excel workbooks with summary and trade details.
- Scripts for generating synthetic gold OHLCV data.

## Requirements

- Python 3.10 or later.
- pip.

Runtime packages used by the project: `backtesting`, `Jinja2`, `matplotlib`, `numpy`, `openpyxl`, `pandas`, `pydantic` (version 2), and `PyYAML`. The Parquet loader also needs a pandas-compatible Parquet engine such as `pyarrow`. Tests use `pytest`.

## Setup

Run these commands from the project directory (the directory containing `cli.py`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install backtesting Jinja2 matplotlib numpy openpyxl pandas "pydantic>=2" PyYAML pytest
```

For Parquet input, install a Parquet engine as well:

```bash
python -m pip install pyarrow
```

## Quick start

Run a configured backtest with the CSV loader (the default):

```bash
python cli.py run --config config/strategies/ma_crossover.yaml
```

Other included strategy configurations:

```bash
python cli.py run --config config/strategies/gold_trend.yaml
python cli.py run --config config/strategies/gold_liquidity_sweep.yaml
```

The CLI prints a short performance summary and writes an HTML report and an Excel workbook to the configured `output_dir` (by default, `reports/output/`). Output filenames are based on the strategy name.

To use Parquet, set an instrument's `data_path` in its YAML configuration to a Parquet file, then choose the Parquet loader:

```bash
python cli.py run --config path/to/your_parquet_config.yaml --loader parquet
```

## Historical data

Each configured instrument must point to an existing data file. CSV files are read with the first column as the timestamp index; Parquet files may contain a timestamp index or column. Both formats must include these case-sensitive columns:

| Column | Description |
| --- | --- |
| `Open` | Bar opening price |
| `High` | Bar high price |
| `Low` | Bar low price |
| `Close` | Bar closing price |
| `Volume` | Optional traded volume |

Timestamps are interpreted or converted to UTC. The loaders reject duplicate timestamps, sort out-of-order data, forward-fill missing values, and apply the configured date range.

The repository includes sample CSV and Parquet files under `data/`. The synthetic data generators can create additional sample inputs:

```bash
python generate_data.py
python generate_fake_gold_data.py
```

By default, these scripts write `data/raw/XAUUSD_M15.csv` and `data/raw/XAUUSD_M1.csv`, respectively. They generate synthetic data for testing the pipeline, not historical market data.

## Configuration

Strategy YAML files live in `config/strategies/`. A configuration describes:

- `instruments`: symbol, timeframe, data path, and optional inclusive start/end dates.
- `risk`: `percent` of equity or a `fixed` cash risk amount per trade, plus the maximum open positions.
- `execution`: initial cash, commission, spread, slippage, and order behavior.
- `session_filter`: optional named UTC trading windows.
- `strategy`: display name, Python strategy class import path, strategy-specific parameters, stop loss, and optional take profit.
- `output_dir`: directory for generated reports.

Supported stop-loss methods are `atr`, `fixed_pct`, and `fixed_points`. Take-profit methods are `rr`, `fixed_pct`, and `fixed_points`. Configuration values and data-file paths are validated when the YAML file is loaded. See the included YAML files for complete examples.

## Adding a strategy

Implement a strategy class based on `BaseStrategy` in `strategy/`. Provide `_setup_indicators()`, `_entry_signal()`, and `_exit_signal()`. Add a YAML configuration whose `strategy.module` points to the class using its dotted Python import path, then run it through `cli.py`.

## Tests

From the project directory, run:

```bash
python -m pytest
```

## Project layout

```text
analytics/       Performance metrics, drawdowns, and breakdowns
config/          Pydantic schemas, shared settings, and strategy YAML files
data/            CSV/Parquet loaders and sample raw/processed data
engine/          Backtest orchestration, broker adapter, sessions, and trade log
reports/         HTML/Excel report builder, charts, and HTML template
strategy/        Base strategy, indicators, and built-in strategies
tests/           Configuration, analytics, and engine tests
cli.py           Command-line backtest runner
generate_data.py Synthetic 15-minute gold data generator
generate_fake_gold_data.py Synthetic 1-minute gold data generator
```
