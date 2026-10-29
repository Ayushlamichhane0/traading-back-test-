"""Structured logging configuration."""
from __future__ import annotations

import logging
import sys
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Clean, formatted console logger with timestamps and levels."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(5)
        name = record.name.rsplit(".", 1)[-1]
        return f"[{timestamp}] [{level}] [{name}] {record.getMessage()}"


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | str | None = None,
) -> None:
    """Configure root logger for the platform."""
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredFormatter())
    root.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
        root.addHandler(file_handler)
