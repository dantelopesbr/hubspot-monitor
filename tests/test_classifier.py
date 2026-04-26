from datetime import datetime, timezone, timedelta
from src.classifier import classify_contact, has_valid_scheduled_activity


def dt(year, month, day, hour=9) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_no_last_contact_no_activity_is_sem_status():
    now = dt(2026, 8, 3, 10)
    record = {'last_contact_at': None, 'next_activity_at': None, 'last_direction': 'OUTBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'SEM_STATUS'
    assert result['urgency_score'] == 0
    assert result['business_days_without_contact'] is None


def test_five_business_days_no_activity_is_critico():
    # Monday → next Monday = 5 business days, no activity → CRITICO
    last = dt(2026, 8, 3)   # Monday
    now = dt(2026, 8, 10)   # next Monday
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'CRITICO'
    assert result['urgency_score'] == 9


def test_five_business_days_with_activity_is_not_critico():
    # 5+ days but has valid activity → EM_ANDAMENTO
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 10)
    future = now + timedelta(hours=24)
    record = {'last_contact_at': last, 'next_activity_at': future, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'EM_ANDAMENTO'
    assert result['urgency_score'] == 0


def test_two_business_days_inbound_is_aguardando_cliente():
    # 2 days < 3 threshold, INBOUND → AGUARDANDO_CLIENTE (not ATENCAO)
    last = dt(2026, 8, 3)   # Monday
    now = dt(2026, 8, 5)    # Wednesday = 2 business days
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'AGUARDANDO_CLIENTE'
    assert result['urgency_score'] == 2


def test_three_business_days_is_atencao():
    # Monday → Thursday = 3 business days → ATENCAO
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 6)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'INBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'ATENCAO'
    assert result['urgency_score'] == 4


def test_two_business_days_outbound_is_em_andamento():
    # 2 days < 3 threshold, OUTBOUND → EM_ANDAMENTO (not ATENCAO)
    last = dt(2026, 8, 3)
    now = dt(2026, 8, 5)
    record = {'last_contact_at': last, 'next_activity_at': None, 'last_direction': 'OUTBOUND'}
    result = classify_contact(record, now=now)
    assert result['status'] == 'EM_ANDAMENTO'
    assert result['urgency_score'] == 1


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
    now = dt(2026, 8, 3, 14)
    slightly_overdue = dt(2026, 8, 3, 10)
    assert has_valid_scheduled_activity(slightly_overdue, now) is True


def test_activity_overdue_more_than_1_business_day_is_invalid():
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
