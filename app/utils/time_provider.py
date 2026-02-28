"""Centralized helpers for obtaining the current datetime."""
from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from typing import Optional

from .database import safe_db_query

UTC_TZ: tzinfo = timezone.utc


def _resolve_timezone(
    *,
    offset_hours: Optional[float] = None,
    tz: Optional[tzinfo] = None,
) -> tzinfo:
    # Project standard: always UTC. Local-time conversion is handled by frontend.
    if tz is not None or offset_hours is not None:
        raise ValueError("Only UTC is supported")

    # Default selalu UTC
    return UTC_TZ


def _db_now_utc() -> datetime:
    """Ambil waktu saat ini dari database dalam UTC.

    Menggunakan database sebagai sumber waktu agar tidak bergantung pada jam sistem aplikasi.
    """

    rows, _ = safe_db_query("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    if not rows:
        raise RuntimeError("Failed to obtain current time from database")
    current = rows[0][0]
    if not isinstance(current, datetime):
        raise TypeError("Database did not return a datetime value")
    # PostgreSQL AT TIME ZONE mengembalikan timestamp tanpa tzinfo (naive)
    return current.replace(tzinfo=UTC_TZ)


def get_current_datetime(
    *,
    offset_hours: Optional[float] = None,
    tz: Optional[tzinfo] = None,
    naive: bool = False,
) -> datetime:
    """Return the current datetime using a unified time source.

    Default selalu mengambil waktu UTC langsung dari database (CURRENT_TIMESTAMP)
    sehingga tidak bergantung pada jam sistem aplikasi.
    """

    base = _db_now_utc()  # aware datetime in UTC

    if tz is not None or offset_hours is not None:
        _resolve_timezone(offset_hours=offset_hours, tz=tz)

    result = base

    return result.replace(tzinfo=None) if naive else result


def get_datetime_from_timestamp(
    timestamp: float,
    *,
    offset_hours: Optional[float] = None,
    tz: Optional[tzinfo] = None,
) -> datetime:
    """Return a timezone-aware datetime from epoch seconds (default UTC)."""
    target_tz = _resolve_timezone(offset_hours=offset_hours, tz=tz)
    try:
        ts_value = float(timestamp)
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp must be numeric") from exc
    return datetime.fromtimestamp(ts_value, tz=target_tz)


def get_current_datetime_string(
    fmt: str = "%Y-%m-%d %H:%M:%S %Z",
    *,
    offset_hours: Optional[float] = None,
    tz: Optional[tzinfo] = None,
) -> str:
    """Return the current datetime formatted according to ``fmt``."""

    # Project standard: always UTC. Validate inputs but do not apply any offset.
    if tz is not None or offset_hours is not None:
        _resolve_timezone(offset_hours=offset_hours, tz=tz)
    return get_current_datetime().strftime(fmt)


__all__ = [
    "get_current_datetime",
    "get_datetime_from_timestamp",
    "get_current_datetime_string",
]
