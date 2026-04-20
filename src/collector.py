import os
from datetime import datetime, timezone, timedelta
from hubspot import HubSpot

CONTACT_PROPERTIES = [
    'firstname', 'lastname', 'email', 'phone',
    'hubspot_owner_id',
    'createdate',
    'notes_last_contacted',
    'hs_email_last_send_date',
    'hs_email_last_reply_date',
    'notes_next_activity_date',
    'origem_do_lead',
]

EXCLUDED_ORIGINS = {'fornecedor', 'transportadora'}
ACTIVE_WINDOW_DAYS = 90


def get_hubspot_client() -> HubSpot:
    return HubSpot(access_token=os.environ['HUBSPOT_ACCESS_TOKEN'])


def parse_hubspot_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        return None


def get_last_direction(contact_props: dict) -> str:
    send_date = parse_hubspot_timestamp(contact_props.get('hs_email_last_send_date'))
    reply_date = parse_hubspot_timestamp(contact_props.get('hs_email_last_reply_date'))
    if reply_date and send_date:
        return 'INBOUND' if reply_date > send_date else 'OUTBOUND'
    if reply_date:
        return 'INBOUND'
    return 'OUTBOUND'


def is_active_contact(contact: dict, now: datetime) -> bool:
    cutoff = now - timedelta(days=ACTIVE_WINDOW_DAYS)
    created = parse_hubspot_timestamp(contact.get('createdate'))
    last_contacted = parse_hubspot_timestamp(contact.get('notes_last_contacted'))
    if created and created >= cutoff:
        return True
    if last_contacted and last_contacted >= cutoff:
        return True
    return False


def is_excluded_origin(contact: dict) -> bool:
    origin = (contact.get('origem_do_lead') or '').strip().lower()
    return origin in EXCLUDED_ORIGINS


def get_all_contacts(client: HubSpot) -> list[dict]:
    contacts = []
    after = None
    while True:
        response = client.crm.contacts.basic_api.get_page(
            limit=100,
            properties=CONTACT_PROPERTIES,
            after=after,
            archived=False,
        )
        for contact in response.results:
            contacts.append({'contact_id': contact.id, **contact.properties})
        if not response.paging:
            break
        after = response.paging.next.after
    return contacts


def get_owner(client: HubSpot, owner_id: str) -> dict:
    try:
        owner = client.crm.owners.owners_api.get_by_id(owner_id=int(owner_id))
        return {
            'owner_name': f'{owner.first_name} {owner.last_name}'.strip(),
            'owner_email': owner.email or '',
        }
    except Exception:
        return {'owner_name': 'Sem responsável', 'owner_email': ''}


def build_contact_records(client: HubSpot, now: datetime | None = None) -> list[dict]:
    if now is None:
        now = datetime.now(timezone.utc)
    contacts = get_all_contacts(client)
    owners_cache: dict[str, dict] = {}
    records = []

    for contact in contacts:
        if is_excluded_origin(contact):
            continue
        if not is_active_contact(contact, now):
            continue

        owner_id = contact.get('hubspot_owner_id')
        if owner_id and owner_id not in owners_cache:
            owners_cache[owner_id] = get_owner(client, owner_id)
        owner = owners_cache.get(owner_id or '', {})

        records.append({
            'contact_id': contact['contact_id'],
            'name': f"{contact.get('firstname') or ''} {contact.get('lastname') or ''}".strip(),
            'email': contact.get('email') or '',
            'phone': contact.get('phone') or '',
            'owner_name': owner.get('owner_name', ''),
            'owner_email': owner.get('owner_email', ''),
            'last_contact_at': parse_hubspot_timestamp(contact.get('notes_last_contacted')),
            'next_activity_at': parse_hubspot_timestamp(contact.get('notes_next_activity_date')),
            'last_direction': get_last_direction(contact),
            'hubspot_url': f'https://app.hubspot.com/contacts/{contact["contact_id"]}',
        })

    return records
