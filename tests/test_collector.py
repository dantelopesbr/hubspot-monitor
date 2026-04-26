# tests/test_collector.py
from datetime import datetime, timezone
from unittest.mock import MagicMock
from src.collector import (
    parse_hubspot_timestamp, is_open_deal, get_last_contact_at,
    get_last_direction, get_all_deals, get_contact, get_owner, build_deal_records,
)


def test_parse_iso_timestamp():
    result = parse_hubspot_timestamp('2026-04-21T09:00:00Z')
    assert result == datetime(2026, 4, 21, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_none_returns_none():
    assert parse_hubspot_timestamp(None) is None


def test_parse_empty_string_returns_none():
    assert parse_hubspot_timestamp('') is None


def test_parse_date_only_returns_utc_midnight():
    result = parse_hubspot_timestamp('2026-04-25')
    assert result == datetime(2026, 4, 25, 0, 0, 0, tzinfo=timezone.utc)


def test_parse_millisecond_timestamp():
    result = parse_hubspot_timestamp('1745783700000')
    assert result is not None
    assert result.tzinfo is not None


def test_is_open_deal_open_stage():
    assert is_open_deal({'dealstage': 'appointmentscheduled'}) is True


def test_is_open_deal_closedwon():
    assert is_open_deal({'dealstage': 'closedwon'}) is False


def test_is_open_deal_closedlost():
    assert is_open_deal({'dealstage': 'closedlost'}) is False


def test_get_last_contact_at_uses_most_recent():
    deal = {'notes_last_contacted': '2026-04-10T00:00:00Z'}
    contacts = [{'notes_last_contacted': '2026-04-20T00:00:00Z', 'hs_last_activity_date': None}]
    result = get_last_contact_at(deal, contacts)
    assert result == datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)


def test_get_last_contact_at_falls_back_to_deal():
    deal = {'notes_last_contacted': '2026-04-20T00:00:00Z'}
    contacts = [{'notes_last_contacted': None, 'hs_last_activity_date': None}]
    result = get_last_contact_at(deal, contacts)
    assert result == datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)


def test_get_last_contact_at_uses_hs_last_activity_date():
    deal = {'notes_last_contacted': None, 'hs_last_activity_date': None}
    contacts = [{'notes_last_contacted': None, 'hs_last_activity_date': '2026-04-25'}]
    result = get_last_contact_at(deal, contacts)
    assert result == datetime(2026, 4, 25, 0, 0, 0, tzinfo=timezone.utc)


def test_get_last_contact_at_all_none():
    assert get_last_contact_at({'notes_last_contacted': None, 'hs_last_activity_date': None}, []) is None


def test_get_last_direction_inbound_when_reply_is_newer():
    contacts = [{
        'hs_email_last_send_date': '2026-04-19T10:00:00Z',
        'hs_email_last_reply_date': '2026-04-20T10:00:00Z',
    }]
    assert get_last_direction(contacts) == 'INBOUND'


def test_get_last_direction_outbound_when_send_is_newer():
    contacts = [{
        'hs_email_last_send_date': '2026-04-20T10:00:00Z',
        'hs_email_last_reply_date': '2026-04-19T10:00:00Z',
    }]
    assert get_last_direction(contacts) == 'OUTBOUND'


def test_get_last_direction_defaults_outbound_no_contacts():
    assert get_last_direction([]) == 'OUTBOUND'


def test_get_contact_returns_empty_on_error():
    mock_client = MagicMock()
    mock_client.crm.contacts.basic_api.get_by_id.side_effect = Exception('API error')
    assert get_contact(mock_client, '99') == {}


def test_get_owner_returns_fallback_on_error():
    mock_client = MagicMock()
    mock_client.crm.owners.owners_api.get_by_id.side_effect = Exception('API error')
    assert get_owner(mock_client, '99') == {'owner_name': 'Sem responsável', 'owner_email': ''}


def _make_deal_mock(deal_id, properties, contact_ids=None):
    deal = MagicMock()
    deal.id = deal_id
    deal.properties = properties
    if contact_ids is not None:
        assoc_result = MagicMock()
        assoc_result.id = contact_ids[0] if contact_ids else None
        contacts_assoc = MagicMock()
        contacts_assoc.results = [MagicMock(id=cid) for cid in contact_ids]
        deal.associations = {'contacts': contacts_assoc}
    else:
        deal.associations = None
    return deal


def test_get_all_deals_paginates():
    mock_client = MagicMock()

    deal1 = _make_deal_mock('10', {
        'dealname': 'Deal A', 'dealstage': 'appointmentscheduled',
        'hubspot_owner_id': '5', 'notes_last_contacted': None,
        'notes_next_activity_date': None, 'hs_last_activity_date': None,
    }, contact_ids=[])
    page1 = MagicMock()
    page1.results = [deal1]
    page1.paging = MagicMock(next=MagicMock(after='cursor1'))

    deal2 = _make_deal_mock('11', {
        'dealname': 'Deal B', 'dealstage': 'closedwon',
        'hubspot_owner_id': '5', 'notes_last_contacted': None,
        'notes_next_activity_date': None, 'hs_last_activity_date': None,
    }, contact_ids=[])
    page2 = MagicMock()
    page2.results = [deal2]
    page2.paging = None

    mock_client.crm.deals.basic_api.get_page.side_effect = [page1, page2]

    result = get_all_deals(mock_client)
    assert len(result) == 2
    assert result[0]['deal_id'] == '10'
    assert result[1]['deal_id'] == '11'
    assert mock_client.crm.deals.basic_api.get_page.call_count == 2


def test_build_deal_records_output_structure():
    mock_client = MagicMock()

    deal = _make_deal_mock('42', {
        'dealname': 'Casa Silva', 'dealstage': 'appointmentscheduled',
        'hubspot_owner_id': '5',
        'notes_last_contacted': '2026-04-20T09:00:00Z',
        'notes_next_activity_date': None,
        'hs_last_activity_date': None,
    }, contact_ids=['99'])
    page = MagicMock()
    page.results = [deal]
    page.paging = None
    mock_client.crm.deals.basic_api.get_page.return_value = page

    contact = MagicMock()
    contact.properties = {
        'firstname': 'Ana', 'lastname': 'Silva', 'email': 'ana@test.com',
        'phone': '11999', 'notes_last_contacted': '2026-04-21T08:00:00Z',
        'hs_last_activity_date': None,
        'hs_email_last_send_date': None, 'hs_email_last_reply_date': None,
    }
    mock_client.crm.contacts.basic_api.get_by_id.return_value = contact

    owner = MagicMock()
    owner.first_name = 'João'
    owner.last_name = 'Vendedor'
    owner.email = 'joao@empresa.com'
    mock_client.crm.owners.owners_api.get_by_id.return_value = owner

    records = build_deal_records(mock_client)

    assert len(records) == 1
    r = records[0]
    assert r['deal_id'] == '42'
    assert r['deal_name'] == 'Casa Silva'
    assert r['deal_stage'] == 'appointmentscheduled'
    assert r['contact_name'] == 'Ana Silva'
    assert r['contact_email'] == 'ana@test.com'
    assert r['owner_name'] == 'João Vendedor'
    assert r['hubspot_url'] == 'https://app.hubspot.com/deal/42'
    assert r['is_open'] is True
    assert r['last_contact_at'] == datetime(2026, 4, 21, 8, 0, 0, tzinfo=timezone.utc)


def test_build_deal_records_closed_deal_marked_not_open():
    mock_client = MagicMock()

    deal = _make_deal_mock('55', {
        'dealname': 'Deal Fechado', 'dealstage': 'closedwon',
        'hubspot_owner_id': None, 'notes_last_contacted': None,
        'notes_next_activity_date': None, 'hs_last_activity_date': None,
    }, contact_ids=[])
    page = MagicMock()
    page.results = [deal]
    page.paging = None
    mock_client.crm.deals.basic_api.get_page.return_value = page

    records = build_deal_records(mock_client)
    assert len(records) == 1
    assert records[0]['is_open'] is False
