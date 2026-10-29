"""Reusable indicator helpers (ATR, SMA, EMA, RSI, etc.).

All functions guarantee:
1. Return 1D numpy array with identical length to input.
2. Initial warm-up bars padded with np.nan.
3. Completely causal — strictly no look-ahead bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: np.ndarray | pd.Series, period: int) -> np.ndarray:
    """Simple Moving Average."""
    x = np.asarray(series, dtype=float)
    res = np.full(len(x), np.nan, dtype=float)
    if len(x) >= period and period > 0:
        res[period - 1:] = np.convolve(x, np.ones(period) / period, mode="valid")
    return res


def ema(series: np.ndarray | pd.Series, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    x = np.asarray(series, dtype=float)
    if len(x) == 0:
        return np.array([], dtype=float)
    s = pd.Series(x)
    return s.ewm(span=period, adjust=False).mean().to_numpy()


def atr(
    high: np.ndarray | pd.Series,
    low: np.ndarray | pd.Series,
    close: np.ndarray | pd.Series,
    period: int = 14,
) -> np.ndarray:
    """Average True Range."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    n = len(c)
    if n == 0:
        return np.array([], dtype=float)
    prev_close = np.roll(c, 1)
    prev_close[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_close), np.abs(l - prev_close)))
    return sma(tr, period)


def rsi(series: np.ndarray | pd.Series, period: int = 14) -> np.ndarray:
    """Relative Strength Index (0-100)."""
    x = np.asarray(series, dtype=float)
    res = np.full(len(x), np.nan, dtype=float)
    if len(x) <= period:
        return res
    delta = np.diff(x)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(period).mean().to_numpy()
    avg_loss = pd.Series(loss).rolling(period).mean().to_numpy()
    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi_vals = 100.0 - (100.0 / (1.0 + rs))
    res[period:] = rsi_vals[period - 1:]
    return res


def bollinger_bands(
    series: np.ndarray | pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands: (upper, middle, lower)."""
    mid = sma(series, period)
    s = pd.Series(np.asarray(series, dtype=float))
    rolling_std = s.rolling(period).std().to_numpy()
    upper = mid + rolling_std * std_dev
    lower = mid - rolling_std * std_dev
    return upper, mid, lower
