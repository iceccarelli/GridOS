"""
Common utility functions for GridOS.

Provides helper functions for data conversion, validation, time
handling, and other cross-cutting concerns.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, TypeVar

T = TypeVar("T")


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier with an optional prefix.

    Parameters
    ----------
    prefix:
        Optional prefix (e.g. ``"dev"`` → ``"dev-a1b2c3d4"``).

    Returns
    -------
    str
        A unique identifier string.
    """
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}-{uid}" if prefix else uid


def kw_to_mw(kw: float) -> float:
    """Convert kilowatts to megawatts."""
    return kw / 1000.0


def mw_to_kw(mw: float) -> float:
    """Convert megawatts to kilowatts."""
    return mw * 1000.0


def kwh_to_mj(kwh: float) -> float:
    """Convert kilowatt-hours to megajoules."""
    return kwh * 3.6


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a value between minimum and maximum."""
    return max(minimum, min(value, maximum))


def power_factor_to_reactive(p_kw: float, pf: float) -> float:
    """Calculate reactive power from active power and power factor.

    Parameters
    ----------
    p_kw:
        Active power in kW.
    pf:
        Power factor (0–1, lagging positive).

    Returns
    -------
    float
        Reactive power in kVAR.
    """
    if pf <= 0 or pf > 1:
        return 0.0
    return p_kw * math.sqrt(1 - pf**2) / pf


def chunk_list(items: Sequence[T], chunk_size: int) -> list[list[T]]:
    """Split a sequence into chunks of the specified size.

    Parameters
    ----------
    items:
        The sequence to split.
    chunk_size:
        Maximum number of items per chunk.

    Returns
    -------
    list[list[T]]
        List of chunks.
    """
    return [list(items[i : i + chunk_size]) for i in range(0, len(items), chunk_size)]


def hash_dict(d: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of a dictionary.

    Parameters
    ----------
    d:
        Dictionary to hash (must be JSON-serialisable).

    Returns
    -------
    str
        Hex-encoded SHA-256 hash.
    """
    import json

    serialised = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning a default on division by zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def moving_average(values: list[float], window: int) -> list[float]:
    """Compute a simple moving average.

    Parameters
    ----------
    values:
        Input values.
    window:
        Window size.

    Returns
    -------
    list[float]
        Moving average values (same length as input, with NaN for
        initial values where the window is incomplete).
    """
    result: list[float] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(float("nan"))
        else:
            avg = sum(values[i - window + 1 : i + 1]) / window
            result.append(avg)
    return result
