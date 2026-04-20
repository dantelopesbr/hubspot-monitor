from datetime import datetime, timedelta
import pytz
import holidays

TIMEZONE = pytz.timezone('America/Sao_Paulo')
BUSINESS_START = 8
BUSINESS_END = 18


def business_hours_between(start: datetime, end: datetime) -> float:
    """Return business hours between start and end (São Paulo, Mon-Fri 8-18h, BR holidays excluded)."""
    if start >= end:
        return 0.0

    start_local = start.astimezone(TIMEZONE)
    end_local = end.astimezone(TIMEZONE)

    br_holidays = holidays.Brazil(
        years=list(range(start_local.year, end_local.year + 1))
    )

    total = 0.0
    current = start_local

    while current.date() <= end_local.date():
        if current.weekday() < 5 and current.date() not in br_holidays:
            day_start = current.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
            day_end = current.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
            period_start = max(current, day_start)
            period_end = min(end_local, day_end)
            if period_start < period_end:
                total += (period_end - period_start).total_seconds() / 3600

        if current.date() == end_local.date():
            break

        next_day = (current + timedelta(days=1)).date()
        current = TIMEZONE.localize(
            datetime(next_day.year, next_day.month, next_day.day, BUSINESS_START, 0, 0)
        )

    return round(total, 2)
