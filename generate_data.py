"""Generate synthetic 15-minute XAUUSD (Gold) data for pipeline testing."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def generate_fake_gold_m15_data(
    output_path: str | Path = "data/raw/XAUUSD_M15.csv",
    n_bars: int = 100_000,
    end_date: str = "2024-12-31",
    mean_price: float = 1950.0,
    seed: int = 42,
) -> Path:
    """Create a synthetic 15-minute gold OHLCV dataset with 100,000 bars."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    np.random.seed(seed)

    # 96 15-minute bars per business day (24h market Monday-Friday)
    bars_per_day = 96
    days_needed = int(np.ceil(n_bars / bars_per_day))
    b_dates = pd.date_range(end=end_date, periods=days_needed, freq="B")

    # Generate 15-minute intervals across all business days
    day_offsets = pd.to_timedelta(np.arange(0, 24 * 60, 15), unit="m")
    all_times = (b_dates.values[:, None] + day_offsets.values[None, :]).ravel()[:n_bars]
    timestamps = pd.to_datetime(all_times, utc=True)

    # Realistic gold price simulation (mean-reverting random walk)
    theta = 0.0002
    sigma = 1.5
    returns = np.random.normal(0, sigma, n_bars)

    close_prices = np.zeros(n_bars)
    close_prices[0] = 1850.0
    for i in range(1, n_bars):
        close_prices[i] = close_prices[i - 1] + theta * (mean_price - close_prices[i - 1]) + returns[i]

    # Open price is previous close shifted
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = 1850.0

    # Intra-bar high and low wiggles
    high_diff = np.abs(np.random.normal(0.8, 0.4, n_bars))
    low_diff = np.abs(np.random.normal(0.8, 0.4, n_bars))

    high_prices = np.maximum(open_prices, close_prices) + high_diff
    low_prices = np.minimum(open_prices, close_prices) - low_diff

    # Volume between 200 and 3500 per 15-minute bar
    volume = np.random.randint(200, 3500, size=n_bars)

    df = pd.DataFrame(
        {
            "datetime": timestamps,
            "Open": np.round(open_prices, 2),
            "High": np.round(high_prices, 2),
            "Low": np.round(low_prices, 2),
            "Close": np.round(close_prices, 2),
            "Volume": volume,
        }
    )

    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} bars of 15m synthetic gold data.")
    print(f"Saved to: {output_path}")
    print(f"Date range: {timestamps[0].strftime('%Y-%m-%d %H:%M')} to {timestamps[-1].strftime('%Y-%m-%d %H:%M')} UTC")
    return output_path


if __name__ == "__main__":
    generate_fake_gold_m15_data()
