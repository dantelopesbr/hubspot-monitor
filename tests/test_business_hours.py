from datetime import datetime, timezone
from src.business_hours import business_days_between


def dt(year, month, day, hour=9) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_same_day_returns_zero():
    assert business_days_between(dt(2026, 8, 3, 9), dt(2026, 8, 3, 17)) == 0


def test_one_business_day():
    # Monday → Tuesday = 1
    assert business_days_between(dt(2026, 8, 3), dt(2026, 8, 4)) == 1


def test_two_business_days():
    # Monday → Wednesday = 2
    assert business_days_between(dt(2026, 8, 3), dt(2026, 8, 5)) == 2


def test_skips_weekend():
    # Friday → Monday = 1 (only Friday counts, Sat/Sun skipped)
    assert business_days_between(dt(2026, 8, 7), dt(2026, 8, 10)) == 1


def test_full_week():
    # Monday → next Monday = 5
    assert business_days_between(dt(2026, 8, 3), dt(2026, 8, 10)) == 5


def test_start_equals_end_returns_zero():
    assert business_days_between(dt(2026, 8, 3), dt(2026, 8, 3)) == 0


def test_start_after_end_returns_zero():
    assert business_days_between(dt(2026, 8, 5), dt(2026, 8, 3)) == 0


def test_weekend_start_to_monday():
    # Saturday → Monday: Saturday is not a business day, so 0 business days elapsed
    assert business_days_between(dt(2026, 8, 8), dt(2026, 8, 10)) == 0
