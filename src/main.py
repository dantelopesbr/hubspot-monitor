import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from .collector import get_hubspot_client, build_contact_records
from .classifier import classify_contact
from .sheets_writer import get_sheets_client, write_snapshot, append_to_history


def run() -> None:
    load_dotenv()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting HubSpot monitor...")

    hubspot = get_hubspot_client()
    print("Fetching contacts from HubSpot...")
    records = build_contact_records(hubspot)
    print(f"  -> {len(records)} contacts fetched")

    print("Classifying contacts...")
    classified = [classify_contact(r) for r in records]

    counts: dict[str, int] = {}
    for r in classified:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    for status, count in sorted(counts.items()):
        print(f"  -> {status}: {count}")

    print("Writing to Google Sheets...")
    sheets = get_sheets_client()
    write_snapshot(sheets, classified)
    append_to_history(sheets, classified)
    print("  -> Done")

    print(f"[SUMMARY] {counts.get('CRITICO', 0)} critical leads out of {len(classified)} total")


if __name__ == '__main__':
    run()
