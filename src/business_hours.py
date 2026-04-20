from datetime import datetime, timedelta


def business_days_between(start: datetime, end: datetime) -> int:
    """Count business days (Mon-Fri) elapsed between start and end. Weekends not counted."""
    if start >= end:
        return 0
    current = start.date()
    end_date = end.date()
    count = 0
    while current < end_date:
        if current.weekday() < 5:  # 0=Mon ... 4=Fri
            count += 1
        current += timedelta(days=1)
    return count
