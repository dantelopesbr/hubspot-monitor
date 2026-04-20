from datetime import datetime, timezone
from unittest.mock import MagicMock
from src.collector import (
    parse_hubspot_timestamp, get_last_direction, get_all_contacts,
    get_owner, build_contact_records, is_active_contact, is_excluded_origin,
)

NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_iso_timestamp():
    result = parse_hubspot_timestamp('2026-04-20T09:00:00Z')
    assert result == datetime(2026, 4, 20, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_none_returns_none():
    assert parse_hubspot_timestamp(None) is None


def test_parse_empty_string_returns_none():
    assert parse_hubspot_timestamp('') is None


def test_get_last_direction_outbound_when_send_is_newer():
    props = {
        'hs_email_last_send_date': '2026-04-20T10:00:00Z',
        'hs_email_last_reply_date': '2026-04-19T10:00:00Z',
    }
    assert get_last_direction(props) == 'OUTBOUND'


def test_get_last_direction_inbound_when_reply_is_newer():
    props = {
        'hs_email_last_send_date': '2026-04-19T10:00:00Z',
        'hs_email_last_reply_date': '2026-04-20T10:00:00Z',
    }
    assert get_last_direction(props) == 'INBOUND'


def test_get_last_direction_defaults_outbound_with_no_dates():
    assert get_last_direction({}) == 'OUTBOUND'


def test_is_active_contact_recent_createdate():
    contact = {'createdate': '2026-04-01T00:00:00Z', 'notes_last_contacted': None}
    assert is_active_contact(contact, NOW) is True


def test_is_active_contact_recent_last_contacted():
    contact = {'createdate': '2025-01-01T00:00:00Z', 'notes_last_contacted': '2026-03-01T00:00:00Z'}
    assert is_active_contact(contact, NOW) is True


def test_is_active_contact_old_contact_excluded():
    contact = {'createdate': '2024-01-01T00:00:00Z', 'notes_last_contacted': None}
    assert is_active_contact(contact, NOW) is False


def test_is_active_contact_no_dates_excluded():
    contact = {'createdate': None, 'notes_last_contacted': None}
    assert is_active_contact(contact, NOW) is False


def test_is_excluded_origin_fornecedor():
    assert is_excluded_origin({'origem_do_lead': 'Fornecedor'}) is True


def test_is_excluded_origin_transportadora():
    assert is_excluded_origin({'origem_do_lead': 'transportadora'}) is True


def test_is_excluded_origin_regular_lead():
    assert is_excluded_origin({'origem_do_lead': 'Indicação'}) is False


def test_is_excluded_origin_none():
    assert is_excluded_origin({'origem_do_lead': None}) is False


def test_get_all_contacts_paginates_through_all_pages():
    mock_client = MagicMock()

    contact1 = MagicMock()
    contact1.id = '1'
    contact1.properties = {
        'firstname': 'Ana', 'lastname': 'Silva', 'email': 'ana@test.com',
        'phone': '', 'hubspot_owner_id': '10',
        'createdate': '2026-04-01T00:00:00Z',
        'notes_last_contacted': None, 'hs_email_last_send_date': None,
        'hs_email_last_reply_date': None, 'notes_next_activity_date': None,
        'origem_do_lead': None,
    }
    contact2 = MagicMock()
    contact2.id = '2'
    contact2.properties = {
        'firstname': 'Bruno', 'lastname': 'Costa', 'email': 'bruno@test.com',
        'phone': '', 'hubspot_owner_id': '10',
        'createdate': '2026-04-01T00:00:00Z',
        'notes_last_contacted': None, 'hs_email_last_send_date': None,
        'hs_email_last_reply_date': None, 'notes_next_activity_date': None,
        'origem_do_lead': None,
    }

    page1 = MagicMock()
    page1.results = [contact1]
    page1.paging = MagicMock(next=MagicMock(after='cursor1'))

    page2 = MagicMock()
    page2.results = [contact2]
    page2.paging = None

    mock_client.crm.contacts.basic_api.get_page.side_effect = [page1, page2]

    result = get_all_contacts(mock_client)
    assert len(result) == 2
    assert result[0]['contact_id'] == '1'
    assert result[1]['contact_id'] == '2'
    assert mock_client.crm.contacts.basic_api.get_page.call_count == 2


def test_get_owner_returns_fallback_on_error():
    mock_client = MagicMock()
    mock_client.crm.owners.owners_api.get_by_id.side_effect = Exception("API error")
    result = get_owner(mock_client, '99')
    assert result == {'owner_name': 'Sem responsável', 'owner_email': ''}


def _make_contact_mock(contact_id, origin=None, createdate='2026-04-01T00:00:00Z'):
    contact = MagicMock()
    contact.id = contact_id
    contact.properties = {
        'firstname': 'Maria', 'lastname': 'Costa', 'email': 'maria@test.com',
        'phone': '11999999999', 'hubspot_owner_id': '5',
        'createdate': createdate,
        'notes_last_contacted': '2026-04-20T09:00:00Z',
        'hs_email_last_send_date': '2026-04-20T09:00:00Z',
        'hs_email_last_reply_date': None,
        'notes_next_activity_date': None,
        'origem_do_lead': origin,
    }
    return contact


def test_build_contact_records_output_structure():
    mock_client = MagicMock()
    page = MagicMock()
    page.results = [_make_contact_mock('42')]
    page.paging = None
    mock_client.crm.contacts.basic_api.get_page.return_value = page

    owner = MagicMock()
    owner.first_name = 'João'
    owner.last_name = 'Vendedor'
    owner.email = 'joao@empresa.com'
    mock_client.crm.owners.owners_api.get_by_id.return_value = owner

    records = build_contact_records(mock_client, now=NOW)

    assert len(records) == 1
    r = records[0]
    assert r['contact_id'] == '42'
    assert r['name'] == 'Maria Costa'
    assert r['email'] == 'maria@test.com'
    assert r['owner_name'] == 'João Vendedor'
    assert r['hubspot_url'] == 'https://app.hubspot.com/contacts/42'
    assert 'last_contact_at' in r
    assert 'next_activity_at' in r
    assert 'last_direction' in r


def test_build_contact_records_excludes_fornecedor():
    mock_client = MagicMock()
    page = MagicMock()
    page.results = [_make_contact_mock('1', origin='Fornecedor')]
    page.paging = None
    mock_client.crm.contacts.basic_api.get_page.return_value = page

    records = build_contact_records(mock_client, now=NOW)
    assert len(records) == 0


def test_build_contact_records_excludes_old_contacts():
    mock_client = MagicMock()
    contact = MagicMock()
    contact.id = '99'
    contact.properties = {
        'firstname': 'Antigo', 'lastname': 'Lead', 'email': 'antigo@test.com',
        'phone': '', 'hubspot_owner_id': None,
        'createdate': '2024-01-01T00:00:00Z',
        'notes_last_contacted': None,
        'hs_email_last_send_date': None,
        'hs_email_last_reply_date': None,
        'notes_next_activity_date': None,
        'origem_do_lead': None,
    }
    page = MagicMock()
    page.results = [contact]
    page.paging = None
    mock_client.crm.contacts.basic_api.get_page.return_value = page

    records = build_contact_records(mock_client, now=NOW)
    assert len(records) == 0
