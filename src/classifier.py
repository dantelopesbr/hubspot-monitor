from datetime import datetime, timezone
from .business_hours import business_days_between

ABANDONMENT_THRESHOLD = 2    # business days → CRITICO
ATTENTION_THRESHOLD = 1      # business days → ATENCAO
ACTIVITY_OVERDUE_THRESHOLD = 1  # business days — activity still considered valid


def has_valid_scheduled_activity(next_activity_at: datetime | None, now: datetime) -> bool:
    """Return True if next_activity_at is future or overdue by less than 1 business day."""
    if next_activity_at is None:
        return False
    if next_activity_at >= now:
        return True
    return business_days_between(next_activity_at, now) < ACTIVITY_OVERDUE_THRESHOLD


def classify_contact(record: dict, now: datetime | None = None) -> dict:
    """Return record with status, urgency_score, business_days_without_contact, has_valid_scheduled_activity added."""
    if now is None:
        now = datetime.now(timezone.utc)

    last_contact_at = record.get('last_contact_at')
    next_activity_at = record.get('next_activity_at')
    last_direction = record.get('last_direction', 'OUTBOUND')

    days = (
        business_days_between(last_contact_at, now)
        if last_contact_at else None
    )

    valid_activity = has_valid_scheduled_activity(next_activity_at, now)

    if valid_activity:
        status, urgency = 'EM_ANDAMENTO', 0
    elif days is None or days >= ABANDONMENT_THRESHOLD:
        status, urgency = 'CRITICO', 9
    elif days >= ATTENTION_THRESHOLD:
        status, urgency = 'ATENCAO', 4
    elif last_direction == 'INBOUND':
        status, urgency = 'AGUARDANDO_CLIENTE', 2
    else:
        status, urgency = 'EM_ANDAMENTO', 1

    return {
        **record,
        'status': status,
        'urgency_score': urgency,
        'business_days_without_contact': days,
        'has_valid_scheduled_activity': valid_activity,
    }
