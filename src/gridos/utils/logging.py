"""
Structured logging utilities for GridOS.

Provides a JSON formatter and convenience functions for configuring
structured logging across the entire GridOS platform.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter.

    Outputs each log record as a single-line JSON object with fields:
    ``timestamp``, ``level``, ``logger``, ``message``, ``module``,
    ``function``, ``line``, and any extra fields attached to the record.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields
        for key in ("device_id", "adapter", "request_id", "user_id", "correlation_id"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the GridOS application.

    Parameters
    ----------
    level:
        Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    json_format:
        If ``True``, use JSON formatting; otherwise use plain text.
    log_file:
        Optional file path for log output (in addition to stdout).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    formatter: logging.Formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for name in ("uvicorn.access", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("gridos").info(
        "Logging configured: level=%s, json=%s, file=%s",
        level,
        json_format,
        log_file,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the ``gridos.`` prefix.

    Parameters
    ----------
    name:
        Logger name (will be prefixed with ``gridos.``).

    Returns
    -------
    logging.Logger
    """
    return logging.getLogger(f"gridos.{name}")
