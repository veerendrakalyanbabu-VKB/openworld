"""Timezone-aware UTC datetime helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time as a naive datetime (preserves existing DB semantics)."""
    return datetime.now(UTC).replace(tzinfo=None)
