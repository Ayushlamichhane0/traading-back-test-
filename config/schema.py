"""Pydantic v2 schema for the entire trading platform.

Every YAML trading plan is validated against these models before the engine
touches data. Invalid configs fail at load time, not mid-backtest.
"""
from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class RiskType(str, Enum):
    PERCENT = "percent"   # risk % of current equity per trade
    FIXED = "fixed"       # fixed cash amount per trade


class RiskConfig(BaseModel):
    type: RiskType = RiskType.PERCENT
    value: float = Field(..., gt=0, description="% of equity or fixed cash per trade")
    max_open_positions: int = Field(1, ge=1)


class SessionWindow(BaseModel):
    """A named UTC time window, e.g. London 07:00–16:00."""
    name: str
    start_utc: time
    end_utc: time

    @model_validator(mode="after")
    def validate_window(self) -> "SessionWindow":
        if self.start_utc >= self.end_utc:
            raise ValueError(f"Session '{self.name}': start_utc must be before end_utc")
        return self


class SessionFilterConfig(BaseModel):
    enabled: bool = False
    windows: list[SessionWindow] = Field(default_factory=list)

    def is_active(self, ts: Any) -> bool:
        """Return True if `ts` falls inside any enabled session window."""
        if not self.enabled:
            return True
        if hasattr(ts, "time"):
            t = ts.time()
        elif isinstance(ts, (datetime, pd.Timestamp)):
            t = ts.time()
        else:
            t = ts
        return any(w.start_utc <= t < w.end_utc for w in self.windows)

    def classify(self, ts: Any) -> str:
        """Return the session name for reporting, or 'off_hours'."""
        if not self.enabled:
            return "all"
        if hasattr(ts, "time"):
            t = ts.time()
        elif isinstance(ts, (datetime, pd.Timestamp)):
            t = ts.time()
        else:
            t = ts
        for w in self.windows:
            if w.start_utc <= t < w.end_utc:
                return w.name
        return "off_hours"


class ExecutionConfig(BaseModel):
    initial_cash: float = Field(100_000.0, gt=0)
    commission: float = Field(0.0002, ge=0, description="Fraction of notional, applied both sides")
    spread: float = Field(0.0, ge=0)
    slippage_ticks: int = Field(0, ge=0)
    trade_on_close: bool = False
    exclusive_orders: bool = True


class InstrumentConfig(BaseModel):
    symbol: str
    timeframe: Timeframe
    data_path: Path
    date_start: date | None = None
    date_end: date | None = None

    @field_validator("data_path")
    @classmethod
    def path_must_exist(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Data file not found: {v}")
        return v


class StopLossConfig(BaseModel):
    method: Literal["atr", "fixed_pct", "fixed_points"]
    value: float = Field(..., gt=0)
    atr_period: int = Field(14, ge=1)


class TakeProfitConfig(BaseModel):
    method: Literal["rr", "fixed_pct", "fixed_points"]
    value: float = Field(..., gt=0)


class StrategyConfig(BaseModel):
    name: str
    module: str = Field(..., description="Dotted import path, e.g. strategy.ma_crossover.MACrossoverStrategy")
    params: dict[str, Any] = Field(default_factory=dict)
    stop_loss: StopLossConfig
    take_profit: TakeProfitConfig | None = None


class PlatformConfig(BaseModel):
    """Root model — the entire trading plan for one backtest run."""
    instruments: list[InstrumentConfig] = Field(..., min_length=1)
    risk: RiskConfig
    execution: ExecutionConfig
    session_filter: SessionFilterConfig = Field(default_factory=SessionFilterConfig)
    strategy: StrategyConfig
    output_dir: Path = Path("reports/output")

    @field_validator("output_dir")
    @classmethod
    def ensure_output_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PlatformConfig":
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls.model_validate(raw)
