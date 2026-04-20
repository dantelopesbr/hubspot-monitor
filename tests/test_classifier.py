from datetime import datetime, timezone, timedelta
from src.classifier import classify_contact, has_valid_scheduled_activity


def dt(year, month, day, hour=9) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_no_last_contact_is_critico():
    now = dt(2026, 8, 3, 10)
    record = {'last_contact_at': None, 'next_activity_at': None, 'last_direction': 'OUTBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'CRITICO'
    assert result['urgency_score'] == 9
    assert result['business_days_without_contact'] is None


def test_two_business_days_is_critico():
    # Monday → Wednesday = 2 business days → CRITICO
    last = dt(2026, 8, 3)   # Monday
    now = dt(2026, 8, 5)    # Wednesday
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'CRITICO'
    assert result['urgency_score'] == 9


def test_one_business_day_is_atencao():
    # Monday → Tuesday = 1 business day → ATENCAO
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 4)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'ATENCAO'
    assert result['urgency_score'] == 4


def test_same_day_outbound_is_em_andamento():
    last = dt(2026, 8, 3, 9)
    now = dt(2026, 8, 3, 14)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'OUTBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'EM_ANDAMENTO'
    assert result['business_days_without_contact'] == 0


def test_same_day_inbound_is_aguardando_cliente():
    last = dt(2026, 8, 3, 9)
    now = dt(2026, 8, 3, 14)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'AGUARDANDO_CLIENTE'
    assert result['urgency_score'] == 2


def test_future_activity_overrides_critico():
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 10)
    future = now + timedelta(hours=24)
    record = {'last_contact_at': last, 'next_activity_at': future, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'EM_ANDAMENTO'
    assert result['urgency_score'] == 0
    assert result['has_valid_scheduled_activity'] is True


def test_activity_overdue_less_than_1_business_day_is_valid():
    # Activity was due same day 4h ago — still valid
    now = dt(2026, 8, 3, 14)
    slightly_overdue = dt(2026, 8, 3, 10)
    assert has_valid_scheduled_activity(slightly_overdue, now) is True


def test_activity_overdue_more_than_1_business_day_is_invalid():
    # Activity due Monday, now Wednesday → 2 business days overdue → invalid
    now = dt(2026, 8, 5)
    very_overdue = dt(2026, 8, 3)
    assert has_valid_scheduled_activity(very_overdue, now) is False


def test_none_activity_returns_false():
    assert has_valid_scheduled_activity(None, dt(2026, 8, 3)) is False


def test_result_includes_business_days_field():
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 4)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'OUTBOUND'}
    result = classify_contact(record, now=now)
    assert result['business_days_without_contact'] == 1
