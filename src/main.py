import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from .collector import get_hubspot_client, build_deal_records
from .classifier import classify_contact
from .sheets_writer import get_sheets_client, write_snapshot, append_to_history


def run() -> None:
    load_dotenv()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting HubSpot monitor...")

    hubspot = get_hubspot_client()
    print("Fetching deals from HubSpot...")
    records = build_deal_records(hubspot)
    print(f"  -> {len(records)} deals fetched")

    print("Classifying deals...")
    classified = [classify_contact(r) for r in records]

    open_deals = [r for r in classified if r.get('is_open')]

    for r in open_deals:
        if r.get('last_contact_at') is None:
            print(f"  [DEBUG] SEM_STATUS deal: {r['deal_id']} | {r['deal_name']} | last_contact_at=None")

    counts: dict[str, int] = {}
    for r in open_deals:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    for status, count in sorted(counts.items()):
        print(f"  -> {status}: {count}")

    print("Writing to Google Sheets...")
    sheets = get_sheets_client()
    write_snapshot(sheets, open_deals)
    append_to_history(sheets, classified)
    print("  -> Done")

    print(f"[SUMMARY] {counts.get('CRITICO', 0)} critical deals out of {len(open_deals)} open deals")


if __name__ == '__main__':
    run()
