# src/collector.py
import os
from datetime import datetime
from hubspot import HubSpot

DEAL_PROPERTIES = [
    'dealname', 'dealstage', 'hubspot_owner_id',
    'notes_last_contacted', 'notes_next_activity_date',
    'hs_last_activity_date',
]

CONTACT_PROPERTIES = [
    'firstname', 'lastname', 'email', 'phone',
    'notes_last_contacted', 'hs_last_activity_date',
    'hs_email_last_send_date', 'hs_email_last_reply_date',
]

CLOSED_STAGES = {'closedwon', 'closedlost'}


def get_hubspot_client() -> HubSpot:
    return HubSpot(access_token=os.environ['HUBSPOT_ACCESS_TOKEN'])


def parse_hubspot_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        return None


def is_open_deal(deal: dict) -> bool:
    return deal.get('dealstage', '') not in CLOSED_STAGES


def get_last_contact_at(deal: dict, contacts: list[dict]) -> datetime | None:
    candidates = [
        parse_hubspot_timestamp(deal.get('notes_last_contacted')),
        parse_hubspot_timestamp(deal.get('hs_last_activity_date')),
    ]
    for c in contacts:
        candidates.append(parse_hubspot_timestamp(c.get('notes_last_contacted')))
        candidates.append(parse_hubspot_timestamp(c.get('hs_last_activity_date')))
    valid = [d for d in candidates if d is not None]
    return max(valid) if valid else None


def get_last_direction(contacts: list[dict]) -> str:
    best_send = None
    best_reply = None
    for c in contacts:
        send = parse_hubspot_timestamp(c.get('hs_email_last_send_date'))
        reply = parse_hubspot_timestamp(c.get('hs_email_last_reply_date'))
        if send and (best_send is None or send > best_send):
            best_send = send
        if reply and (best_reply is None or reply > best_reply):
            best_reply = reply
    if best_reply and best_send:
        return 'INBOUND' if best_reply > best_send else 'OUTBOUND'
    if best_reply:
        return 'INBOUND'
    return 'OUTBOUND'


def get_all_deals(client: HubSpot) -> list[dict]:
    deals = []
    after = None
    while True:
        response = client.crm.deals.basic_api.get_page(
            limit=100,
            properties=DEAL_PROPERTIES,
            after=after,
            archived=False,
        )
        for deal in response.results:
            deals.append({'deal_id': deal.id, **deal.properties})
        if not response.paging:
            break
        after = response.paging.next.after
    return deals


def get_associated_contact_ids(client: HubSpot, deal_id: str) -> list[str]:
    try:
        response = client.crm.deals.associations_api.get_all(
            deal_id=int(deal_id),
            to_object_type='contacts',
        )
        return [str(a.id) for a in (response.results or [])]
    except Exception:
        return []


def get_contact(client: HubSpot, contact_id: str) -> dict:
    try:
        contact = client.crm.contacts.basic_api.get_by_id(
            contact_id=contact_id,
            properties=CONTACT_PROPERTIES,
        )
        return contact.properties or {}
    except Exception:
        return {}


def get_owner(client: HubSpot, owner_id: str) -> dict:
    try:
        owner = client.crm.owners.owners_api.get_by_id(owner_id=int(owner_id))
        return {
            'owner_name': f'{owner.first_name} {owner.last_name}'.strip(),
            'owner_email': owner.email or '',
        }
    except Exception:
        return {'owner_name': 'Sem responsável', 'owner_email': ''}


def build_deal_records(client: HubSpot) -> list[dict]:
    deals = get_all_deals(client)
    contacts_cache: dict[str, dict] = {}
    owners_cache: dict[str, dict] = {}
    records = []

    for deal in deals:
        deal_id = deal['deal_id']

        contact_ids = get_associated_contact_ids(client, deal_id)
        contacts = []
        for cid in contact_ids:
            if cid not in contacts_cache:
                contacts_cache[cid] = get_contact(client, cid)
            contacts.append(contacts_cache[cid])

        owner_id = deal.get('hubspot_owner_id')
        if owner_id and owner_id not in owners_cache:
            owners_cache[owner_id] = get_owner(client, owner_id)
        owner = owners_cache.get(owner_id or '', {})

        primary = contacts[0] if contacts else {}

        records.append({
            'deal_id': deal_id,
            'deal_name': deal.get('dealname') or '',
            'deal_stage': deal.get('dealstage') or '',
            'contact_name': f"{primary.get('firstname') or ''} {primary.get('lastname') or ''}".strip(),
            'contact_email': primary.get('email') or '',
            'contact_phone': primary.get('phone') or '',
            'owner_name': owner.get('owner_name', ''),
            'owner_email': owner.get('owner_email', ''),
            'last_contact_at': get_last_contact_at(deal, contacts),
            'next_activity_at': parse_hubspot_timestamp(deal.get('notes_next_activity_date')),
            'last_direction': get_last_direction(contacts),
            'hubspot_url': f'https://app.hubspot.com/deal/{deal_id}',
            'is_open': is_open_deal(deal),
        })

    return records
