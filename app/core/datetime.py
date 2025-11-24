from datetime import UTC, datetime


def utc_now() -> datetime:
    """Get the current UTC datetime."""
    return datetime.now(UTC)


def utc(value: datetime) -> datetime:
    """
    Convert a datetime to UTC.

    - If naive (no timezone): assumes it's already UTC and adds UTC timezone
    - If timezone-aware: converts to UTC

    Args:
        value: Datetime to convert to UTC

    Returns:
        UTC timezone-aware datetime
    """
    if value.tzinfo is None:
        # Naive datetime - assume it's UTC and add timezone
        return value.replace(tzinfo=UTC)
    else:
        # Timezone-aware - convert to UTC (this fixes the bug!)
        return value.astimezone(UTC)
