#!/usr/bin/env python3
"""
Migration script for converting single-user Firestore data to multi-user structure.

This script:
1. Backs up existing collections to JSON files
2. Copies all documents to user-scoped subcollections (users/{userId}/...)
3. Verifies document counts match
4. Legacy collections remain but are blocked by Firestore rules

Usage:
    python scripts/migrate_to_multiuser.py --owner-uid YOUR_FIREBASE_UID

Before running:
1. Create your Firebase Auth account (via frontend or Firebase Console)
2. Get your Firebase Auth UID from the Firebase Console > Authentication > Users
3. Set FIREBASE_KEY environment variable (or ensure .env has it)

The script does NOT delete original data - it copies to the new structure.
Original data is blocked by updated Firestore rules anyway.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(override=True)

import firebase_admin
from firebase_admin import credentials, firestore

# Collections to migrate (user-scoped in new structure)
COLLECTIONS_TO_MIGRATE = [
    "expenses",
    "budget_caps",
    "recurring_expenses",
    "pending_expenses",
    "budget_alert_tracking"
]


def init_firebase():
    """Initialize Firebase Admin SDK."""
    if firebase_admin._apps:
        return firestore.client()

    # Get Firebase credentials
    firebase_key = os.getenv('FIREBASE_KEY')
    if not firebase_key:
        raise ValueError("FIREBASE_KEY environment variable not set")

    # Try to parse as JSON string first, otherwise treat as file path
    try:
        # Use strict=False to allow control characters (like newlines in private key)
        cred_dict = json.loads(firebase_key, strict=False)
        cred = credentials.Certificate(cred_dict)
    except json.JSONDecodeError:
        # Assume it's a file path
        cred = credentials.Certificate(firebase_key)

    firebase_admin.initialize_app(cred)
    return firestore.client()


def backup_collection(db, collection_name: str, backup_dir: Path) -> list:
    """
    Backup a collection to a JSON file.

    Args:
        db: Firestore client
        collection_name: Name of collection to backup
        backup_dir: Directory to save backup files

    Returns:
        List of document dictionaries
    """
    print(f"  Backing up {collection_name}...")
    docs = []

    collection_ref = db.collection(collection_name)
    for doc in collection_ref.stream():
        doc_data = doc.to_dict()
        doc_data['_id'] = doc.id
        docs.append(doc_data)

    # Save to JSON file
    backup_file = backup_dir / f"{collection_name}_backup.json"
    with open(backup_file, 'w') as f:
        json.dump(docs, f, indent=2, default=str)

    print(f"    Saved {len(docs)} documents to {backup_file}")
    return docs


def migrate_collection(db, collection_name: str, owner_uid: str, docs: list) -> int:
    """
    Copy documents to user-scoped subcollection.

    Args:
        db: Firestore client
        collection_name: Original collection name
        owner_uid: Firebase Auth UID of the owner
        docs: List of documents to migrate

    Returns:
        Number of documents migrated
    """
    print(f"  Migrating {collection_name} to users/{owner_uid}/{collection_name}...")

    # Target collection path
    target_collection = db.collection("users").document(owner_uid).collection(collection_name)

    migrated = 0
    for doc_data in docs:
        doc_id = doc_data.pop('_id')

        # Remove any internal fields that shouldn't be copied
        clean_data = {k: v for k, v in doc_data.items() if not k.startswith('_')}

        # Copy to new location
        target_collection.document(doc_id).set(clean_data)
        migrated += 1

    print(f"    Migrated {migrated} documents")
    return migrated


def verify_migration(db, collection_name: str, owner_uid: str, expected_count: int) -> bool:
    """
    Verify that migration was successful.

    Args:
        db: Firestore client
        collection_name: Collection name
        owner_uid: Firebase Auth UID
        expected_count: Expected number of documents

    Returns:
        True if counts match
    """
    target_collection = db.collection("users").document(owner_uid).collection(collection_name)
    actual_count = len(list(target_collection.stream()))

    if actual_count == expected_count:
        print(f"    {collection_name}: {actual_count} documents (verified)")
        return True
    else:
        print(f"    {collection_name}: MISMATCH - expected {expected_count}, got {actual_count}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate single-user Firestore data to multi-user structure"
    )
    parser.add_argument(
        "--owner-uid",
        required=True,
        help="Firebase Auth UID of the owner (your user ID)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only backup data, don't migrate"
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Directory for backup files (default: backups)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Multi-User Migration Script")
    print("=" * 60)
    print(f"\nOwner UID: {args.owner_uid}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Initialize Firebase
    print("Initializing Firebase...")
    db = init_firebase()
    print("Connected to Firestore")
    print()

    # Create backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(args.backup_dir) / f"migration_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"Backup directory: {backup_dir}")
    print()

    # Phase 1: Backup all collections
    print("Phase 1: Backing up existing data")
    print("-" * 40)
    collection_data = {}
    for collection_name in COLLECTIONS_TO_MIGRATE:
        docs = backup_collection(db, collection_name, backup_dir)
        collection_data[collection_name] = docs
    print()

    if args.dry_run:
        print("Dry run complete. Backups saved, no migration performed.")
        print()
        print("To perform the actual migration, run without --dry-run flag.")
        return

    # Phase 2: Migrate to user-scoped collections
    print("Phase 2: Migrating to user-scoped collections")
    print("-" * 40)
    for collection_name, docs in collection_data.items():
        if docs:
            migrate_collection(db, collection_name, args.owner_uid, docs)
        else:
            print(f"  {collection_name}: No documents to migrate")
    print()

    # Phase 3: Verify migration
    print("Phase 3: Verifying migration")
    print("-" * 40)
    all_verified = True
    for collection_name, docs in collection_data.items():
        if docs:
            if not verify_migration(db, collection_name, args.owner_uid, len(docs)):
                all_verified = False
        else:
            print(f"    {collection_name}: Skipped (no documents)")
    print()

    # Summary
    print("=" * 60)
    if all_verified:
        print("Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Deploy updated firestore.rules:")
        print("   firebase deploy --only firestore:rules")
        print()
        print("2. Enable Firebase Auth providers in Firebase Console:")
        print("   - Email/Password")
        print("   - Google Sign-In")
        print()
        print("3. Add your Cloud Run URL to authorized domains in Firebase Console")
        print()
        print("4. Deploy the updated backend:")
        print("   gcloud run deploy ...")
    else:
        print("Migration completed with WARNINGS - please verify data manually")
        print(f"Backups are available in: {backup_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
