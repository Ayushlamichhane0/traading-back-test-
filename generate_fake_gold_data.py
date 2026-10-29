"""Generate synthetic 1-minute XAUUSD data for pipeline testing."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def generate_fake_gold_data(
    output_path: str | Path = "data/raw/XAUUSD_M1.csv",
    start_date: str = "2023-01-02",
    days: int = 14,
    base_price: float = 1850.0,
    seed: int = 42,
) -> Path:
    """Create a synthetic 1-minute gold OHLCV dataset."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    np.random.seed(seed)
    
    # Generate business days only (gold market is closed on weekends)
    dates = pd.date_range(start=start_date, periods=days, freq="B")
    all_dfs = []

    current_price = base_price

    for date in dates:
        # 1440 minutes in a day (00:00 to 23:59 UTC)
        timestamps = pd.date_range(
            start=f"{date.strftime('%Y-%m-%d')} 00:00:00",
            end=f"{date.strftime('%Y-%m-%d')} 23:59:00",
            freq="1min",
            tz="UTC",
        )
        n = len(timestamps)
        
        # Intra-day random walk with mean-reverting drifts
        drift = np.sin(np.linspace(0, 2 * np.pi, n)) * 0.05
        minute_returns = np.random.normal(loc=0.0, scale=0.3, size=n) + drift
        close_prices = current_price + np.cumsum(minute_returns)
        
        # Wiggle around close to create Open, High, Low
        high_diff = np.abs(np.random.normal(loc=0.3, scale=0.2, size=n))
        low_diff = np.abs(np.random.normal(loc=0.3, scale=0.2, size=n))
        
        high_prices = close_prices + high_diff
        low_prices = close_prices - low_diff
        
        # Open price is previous close shifted (or slight gap)
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = current_price
        
        # Ensure High >= max(Open, Close) and Low <= min(Open, Close)
        high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
        low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
        
        volume = np.random.randint(100, 1500, size=n)
        
        df_day = pd.DataFrame(
            {
                "datetime": timestamps,
                "Open": np.round(open_prices, 2),
                "High": np.round(high_prices, 2),
                "Low": np.round(low_prices, 2),
                "Close": np.round(close_prices, 2),
                "Volume": volume,
            }
        )
        all_dfs.append(df_day)
        current_price = close_prices[-1]

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all.to_csv(output_path, index=False)
    print(f"Generated {len(df_all):,} bars of synthetic gold data at: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_fake_gold_data()
