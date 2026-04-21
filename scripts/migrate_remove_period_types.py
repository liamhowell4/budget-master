#!/usr/bin/env python3
"""
Migration script: remove retired budget period fields.

Deletes the following fields from every users/{uid} Firestore document:
- budget_period_type
- budget_week_start_day
- budget_biweekly_anchor

These used to let a user pick a weekly or biweekly budget cadence; the app now
only supports monthly periods with a configurable start day (1..28 or "last").
`budget_month_start_day` is left untouched — for users who previously selected
weekly/biweekly this field already defaults to 1 on read.

Idempotent: safe to re-run. Firestore.DELETE_FIELD is a no-op when the field
is already absent.

Usage:
    python scripts/migrate_remove_period_types.py            # apply changes
    python scripts/migrate_remove_period_types.py --dry-run  # report only
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path so we can import project modules if needed.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(override=True)

import firebase_admin
from firebase_admin import credentials, firestore


RETIRED_FIELDS = (
    "budget_period_type",
    "budget_week_start_day",
    "budget_biweekly_anchor",
)


def init_firebase() -> firestore.Client:
    if not firebase_admin._apps:
        key = os.getenv("FIREBASE_KEY")
        if not key:
            print("ERROR: FIREBASE_KEY environment variable is not set.")
            sys.exit(1)
        if os.path.isfile(key):
            cred = credentials.Certificate(key)
        else:
            import json
            cred = credentials.Certificate(json.loads(key))
        firebase_admin.initialize_app(cred)
    return firestore.client()


def run(dry_run: bool) -> None:
    db = init_firebase()
    users = db.collection("users").stream()

    total = 0
    touched = 0
    for doc in users:
        total += 1
        data = doc.to_dict() or {}
        present = [f for f in RETIRED_FIELDS if f in data]
        if not present:
            continue

        touched += 1
        before = {f: data[f] for f in present}
        print(f"[uid={doc.id}] retiring fields: {before}")
        if not dry_run:
            update = {f: firestore.DELETE_FIELD for f in present}
            db.collection("users").document(doc.id).update(update)

    mode = "(dry-run)" if dry_run else "(applied)"
    print(f"\nScanned {total} user documents; {touched} had retired fields {mode}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
