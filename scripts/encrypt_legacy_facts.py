"""
CORTEX Security — Encrypt Legacy Plaintext Facts.

Scans the database for facts whose `content` field does NOT start with the
AES-256-GCM prefix (`v6_aesgcm:`) and encrypts them in-place.

Usage:
    cd ~/cortex && .venv/bin/python scripts/encrypt_legacy_facts.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Ensure cortex package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cortex.crypto import get_default_encrypter  # noqa: E402

PREFIX = "v6_aesgcm:"
DB_PATH = Path.home() / ".cortex" / "cortex.db"


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt legacy plaintext facts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="DB path")
    args = parser.parse_args()

    enc = get_default_encrypter()
    if not enc.is_active:
        print("ERROR: No CORTEX_MASTER_KEY set. Cannot encrypt.")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Find all plaintext facts (content NOT starting with v6_aesgcm:)
    cursor = conn.execute(
        "SELECT id, content, meta, tenant_id FROM facts "
        "WHERE content IS NOT NULL AND content != '' "
        "AND content NOT LIKE ?",
        (f"{PREFIX}%",),
    )
    rows = cursor.fetchall()

    print(f"Found {len(rows)} plaintext facts to encrypt.")

    if args.dry_run:
        for row in rows[:10]:
            preview = row["content"][:80].replace("\n", "\\n")
            print(f"  [DRY] Fact #{row['id']}: {preview}...")
        if len(rows) > 10:
            print(f"  ... and {len(rows) - 10} more")
        return

    encrypted = 0
    errors = 0

    for row in rows:
        try:
            tenant_id = row["tenant_id"] or "default"
            new_content = enc.encrypt_str(row["content"], tenant_id=tenant_id)

            # Also encrypt meta if it's plaintext JSON
            meta_val = row["meta"]
            new_meta = meta_val
            if meta_val and not meta_val.startswith(PREFIX):
                new_meta = enc.encrypt_str(meta_val, tenant_id=tenant_id)

            conn.execute(
                "UPDATE facts SET content = ?, meta = ? WHERE id = ?",
                (new_content, new_meta, row["id"]),
            )
            encrypted += 1
        except Exception as e:
            print(f"  ERROR on fact #{row['id']}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"Done. Encrypted: {encrypted}. Errors: {errors}.")


if __name__ == "__main__":
    main()
