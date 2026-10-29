"""Trading session definitions and utilities.

Common global market sessions (UTC times):
- Asia / Tokyo:    00:00 - 07:00 UTC
- London:          07:00 - 13:00 UTC (or through 16:00 UTC)
- New York:        13:00 - 21:00 UTC
- Overlap (LDN/NY):13:00 - 16:00 UTC
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any

import pandas as pd

from config.schema import SessionFilterConfig, SessionWindow

# Standard reference windows in UTC
DEFAULT_SESSIONS = [
    SessionWindow(name="Asia", start_utc=time(0, 0), end_utc=time(7, 0)),
    SessionWindow(name="London", start_utc=time(7, 0), end_utc=time(13, 0)),
    SessionWindow(name="New_York", start_utc=time(13, 0), end_utc=time(21, 0)),
]


def create_default_session_filter(enabled: bool = True) -> SessionFilterConfig:
    """Create a standard session filter with Asia, London, and NY windows."""
    return SessionFilterConfig(enabled=enabled, windows=DEFAULT_SESSIONS)


def classify_session(ts: Any, windows: list[SessionWindow] | None = None) -> str:
    """Classify a given timestamp into a market session."""
    if hasattr(ts, "time"):
        t = ts.time()
    elif isinstance(ts, (datetime, pd.Timestamp)):
        t = ts.time()
    else:
        t = ts

    sessions = windows or DEFAULT_SESSIONS
    for w in sessions:
        if w.start_utc <= t < w.end_utc:
            return w.name
    return "off_hours"
