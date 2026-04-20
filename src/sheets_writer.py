import json
import os
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SNAPSHOT_HEADERS = [
    'contact_id', 'name', 'email', 'phone',
    'owner_name', 'owner_email',
    'last_contact_at', 'business_days_without_contact',
    'status', 'urgency_score', 'has_valid_scheduled_activity',
    'hubspot_url',
]

HISTORY_HEADERS = ['snapshot_date'] + SNAPSHOT_HEADERS


def get_sheets_client() -> gspread.Client:
    creds_dict = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _record_to_row(record: dict, headers: list[str]) -> list[str]:
    row = []
    for h in headers:
        val = record.get(h, '')
        if isinstance(val, datetime):
            val = val.strftime('%Y-%m-%d %H:%M:%S')
        elif val is None:
            val = ''
        else:
            val = str(val)
        row.append(val)
    return row


def write_snapshot(client: gspread.Client, records: list[dict]) -> None:
    """Overwrite the 'snapshot' tab with current state of all contacts."""
    sheet = client.open_by_key(os.environ['GOOGLE_SHEETS_ID']).worksheet('snapshot')
    sheet.clear()
    rows = [SNAPSHOT_HEADERS] + [_record_to_row(r, SNAPSHOT_HEADERS) for r in records]
    sheet.update('A1', rows)


def append_to_history(client: gspread.Client, records: list[dict]) -> None:
    """Append today's classified records to the 'historico' tab."""
    sheet = client.open_by_key(os.environ['GOOGLE_SHEETS_ID']).worksheet('historico')
    today = date.today().isoformat()
    rows = [_record_to_row({'snapshot_date': today, **r}, HISTORY_HEADERS) for r in records]
    if rows:
        sheet.append_rows(rows, value_input_option='USER_ENTERED')
