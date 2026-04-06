"""Date and timezone helpers."""

from datetime import date, datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))


def now_msk() -> datetime:
    """Current datetime in Moscow timezone."""
    return datetime.now(MSK)


def today_msk() -> date:
    """Current date in Moscow timezone."""
    return now_msk().date()
