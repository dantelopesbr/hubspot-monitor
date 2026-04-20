from datetime import datetime
import pytz
from src.business_hours import business_hours_between

TZ = pytz.timezone('America/Sao_Paulo')


def dt(year, month, day, hour=8, minute=0) -> datetime:
    return TZ.localize(datetime(year, month, day, hour, minute))


def test_same_day_within_business_hours():
    # Monday 9h → 11h = 2 hours
    assert business_hours_between(dt(2026, 8, 3, 9), dt(2026, 8, 3, 11)) == 2.0


def test_across_two_business_days():
    # Monday 16h → Tuesday 10h: Mon=2h + Tue=2h = 4h
    assert business_hours_between(dt(2026, 8, 3, 16), dt(2026, 8, 4, 10)) == 4.0


def test_skips_weekend():
    # Friday 16h → Monday 10h: Fri=2h + Mon=2h = 4h (skip Sat/Sun)
    assert business_hours_between(dt(2026, 8, 7, 16), dt(2026, 8, 10, 10)) == 4.0


def test_skips_brazilian_national_holiday():
    # Sep 7 = Independence Day. Fri Sep 4 16h → Tue Sep 8 10h:
    # Fri=2h, Mon Sep 7(holiday)=0h, Tue=2h = 4h
    assert business_hours_between(dt(2026, 9, 4, 16), dt(2026, 9, 8, 10)) == 4.0


def test_start_equals_end_returns_zero():
    assert business_hours_between(dt(2026, 8, 3, 9), dt(2026, 8, 3, 9)) == 0.0


def test_start_after_end_returns_zero():
    assert business_hours_between(dt(2026, 8, 3, 11), dt(2026, 8, 3, 9)) == 0.0


def test_clamps_to_business_hours_same_day():
    # Start 6h, end 22h → only 8h-18h counts = 10h
    assert business_hours_between(dt(2026, 8, 3, 6), dt(2026, 8, 3, 22)) == 10.0


def test_48_business_hours_span():
    # Mon Aug 3 9h → Fri Aug 7 17h:
    # Mon=9h, Tue=10h, Wed=10h, Thu=10h, Fri(8h-17h)=9h = 48h
    assert business_hours_between(dt(2026, 8, 3, 9), dt(2026, 8, 7, 17)) == 48.0
