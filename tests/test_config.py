"""Unit tests for config/schema.py."""
from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.schema import (
    InstrumentConfig,
    PlatformConfig,
    RiskConfig,
    RiskType,
    SessionFilterConfig,
    SessionWindow,
    Timeframe,
)


def test_session_window_validation():
    """Test start_utc must be strictly before end_utc."""
    # Valid window
    w = SessionWindow(name="Valid", start_utc=time(8, 0), end_utc=time(16, 0))
    assert w.name == "Valid"

    # Invalid window: start == end
    with pytest.raises(ValidationError):
        SessionWindow(name="Invalid", start_utc=time(8, 0), end_utc=time(8, 0))

    # Invalid window: start > end
    with pytest.raises(ValidationError):
        SessionWindow(name="Invalid", start_utc=time(17, 0), end_utc=time(8, 0))


def test_session_filter_classification():
    """Test session classification and active state logic."""
    sf = SessionFilterConfig(
        enabled=True,
        windows=[
            SessionWindow(name="London", start_utc=time(8, 0), end_utc=time(16, 0)),
            SessionWindow(name="NY", start_utc=time(16, 0), end_utc=time(22, 0)),
        ],
    )
    t_london = time(10, 30)
    t_ny = time(18, 0)
    t_off = time(3, 0)

    assert sf.is_active(t_london) is True
    assert sf.classify(t_london) == "London"

    assert sf.is_active(t_ny) is True
    assert sf.classify(t_ny) == "NY"

    assert sf.is_active(t_off) is False
    assert sf.classify(t_off) == "off_hours"


def test_missing_data_path_raises(tmp_path: Path):
    """Test that InstrumentConfig fails when data file does not exist."""
    missing_file = tmp_path / "does_not_exist.csv"
    with pytest.raises(ValidationError) as exc:
        InstrumentConfig(
            symbol="TEST",
            timeframe=Timeframe.H1,
            data_path=missing_file,
        )
    assert "Data file not found" in str(exc.value)


def test_risk_config_validation():
    """Test risk value must be positive."""
    # Valid
    rc = RiskConfig(type=RiskType.PERCENT, value=1.5, max_open_positions=1)
    assert rc.value == 1.5

    # Invalid value <= 0
    with pytest.raises(ValidationError):
        RiskConfig(type=RiskType.PERCENT, value=0.0, max_open_positions=1)


def test_load_default_strategy_yaml():
    """Test loading existing ma_crossover.yaml."""
    yaml_path = Path("config/strategies/ma_crossover.yaml")
    if yaml_path.exists():
        cfg = PlatformConfig.from_yaml(yaml_path)
        assert cfg.strategy.name == "MA Crossover"
        assert len(cfg.instruments) >= 1
