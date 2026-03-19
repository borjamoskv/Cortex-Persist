"""Migration: Collapse facts table from 32 → 21 columns.

Folds 11 orphan/low-use columns into the `metadata` JSON field.
Keeps 21 columns: the 16 DDL-defined + 5 deeply-wired extras.

DESTRUCTIVE. Requires backup. Run via: python3 tools/migrate_32_to_21.py
"""

import json
import os
import sqlite3
import sys

DB_PATH = os.path.expanduser("~/.cortex/cortex.db")

# 11 columns to fold into metadata JSON
FOLD_COLUMNS = [
    "is_bridge",
    "success_rate",
    "source_metadata",
    "access_stats",
    "exergy",
    "pinned",
    "verification_status",
    "provenance_json",
    "claims_json",
    "signatures_json",
    "last_revalidated_at",
]

# 21 columns to keep as real DB columns
KEEP_COLUMNS = [
    "id",
    "tenant_id",
    "project",
    "content",
    "fact_type",
    "tags",
    "metadata",
    "timestamp",
    "cognitive_layer",
    "parent_decision_id",
    "is_diamond",
    "confidence",
    "tx_id",
    "hash",
    "valid_from",
    "valid_until",
    "source",
    "created_at",
    "updated_at",
    "is_tombstoned",
    "is_quarantined",
]


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")

    # Verify current schema
    cols = [r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()]
    print(f"Current columns: {len(cols)}")

    if len(cols) <= 21:
        print(f"Already at {len(cols)} columns. Nothing to do.")
        conn.close()
        return

    # Check all fold columns exist
    missing = [c for c in FOLD_COLUMNS if c not in cols]
    if missing:
        print(f"ERROR: Missing columns to fold: {missing}")
        conn.close()
        sys.exit(1)

    # Phase 1: Merge fold columns into metadata JSON for each row
    print("Phase 1: Folding 11 columns into metadata JSON...")
    rows = conn.execute(
        "SELECT id, metadata, " + ", ".join(FOLD_COLUMNS) + " FROM facts"
    ).fetchall()
    print(f"  Processing {len(rows)} rows...")

    for row in rows:
        fact_id = row["id"]
        raw_meta = row["metadata"]

        # Parse existing metadata
        try:
            meta = json.loads(raw_meta) if raw_meta else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}

        # Fold each column value into metadata (skip None/default values)
        for col in FOLD_COLUMNS:
            val = row[col]
            if val is None:
                continue

            # Parse JSON text columns
            if col in (
                "source_metadata",
                "access_stats",
                "provenance_json",
                "claims_json",
                "signatures_json",
            ):
                try:
                    parsed = json.loads(val) if isinstance(val, str) else val
                    # Skip empty defaults
                    if parsed in ({}, [], "{}", "[]"):
                        continue
                    meta[col] = parsed
                except (json.JSONDecodeError, TypeError):
                    if val not in ("{}", "[]"):
                        meta[col] = val
            elif col == "verification_status" and val == "unsupported":
                continue  # Skip default value
            elif col == "pinned" and val == 0:
                continue  # Skip default
            elif col == "exergy" and val == 0.0:
                continue  # Skip default
            elif col == "success_rate" and val == 1.0:
                continue  # Skip default
            elif col == "is_bridge" and val == 0:
                continue  # Skip default
            elif col == "last_revalidated_at" and not val:
                continue  # Skip empty
            else:
                meta[col] = val

        # Write merged metadata back
        new_meta = json.dumps(meta, separators=(",", ":"))
        conn.execute("UPDATE facts SET metadata = ? WHERE id = ?", (new_meta, fact_id))

    conn.commit()
    print("  ✅ Metadata merged for all rows.")

    # Phase 2: Create new table with 21 columns
    print("Phase 2: Creating new facts table with 21 columns...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts_migrated (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id           TEXT    NOT NULL DEFAULT 'default',
            project             TEXT    NOT NULL,
            content             TEXT    NOT NULL,
            fact_type           TEXT    NOT NULL DEFAULT 'knowledge',
            tags                TEXT    NOT NULL DEFAULT '[]',
            metadata            TEXT             DEFAULT '{}',
            timestamp           REAL    NOT NULL DEFAULT (strftime('%s', 'now')),
            cognitive_layer     TEXT             DEFAULT 'semantic',
            parent_decision_id  INTEGER,
            is_diamond          INTEGER NOT NULL DEFAULT 0,
            confidence          TEXT             DEFAULT 'C5',
            tx_id               INTEGER,
            hash                TEXT,
            valid_from          TEXT,
            valid_until         TEXT,
            source              TEXT,
            created_at          TEXT    NOT NULL DEFAULT '',
            updated_at          TEXT    NOT NULL DEFAULT '',
            is_tombstoned       INTEGER NOT NULL DEFAULT 0,
            is_quarantined      INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Phase 3: Copy data
    print("Phase 3: Copying data to new table...")
    keep_cols_str = ", ".join(KEEP_COLUMNS)
    conn.execute(f"INSERT INTO facts_migrated ({keep_cols_str}) SELECT {keep_cols_str} FROM facts")
    conn.commit()

    # Verify row count
    old_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    new_count = conn.execute("SELECT COUNT(*) FROM facts_migrated").fetchone()[0]
    print(f"  Old: {old_count} rows, New: {new_count} rows")

    if old_count != new_count:
        print("ERROR: Row count mismatch! Aborting.")
        conn.execute("DROP TABLE facts_migrated")
        conn.commit()
        conn.close()
        sys.exit(1)

    # Phase 4: Swap tables
    print("Phase 4: Swapping tables...")
    conn.execute("ALTER TABLE facts RENAME TO facts_old_32col")
    conn.execute("ALTER TABLE facts_migrated RENAME TO facts")
    conn.commit()

    # Phase 5: Recreate indexes
    print("Phase 5: Recreating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_hash ON facts(hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tombstoned ON facts(is_tombstoned)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tenant_project ON facts(tenant_id, project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_cognitive_layer ON facts(cognitive_layer)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tx_id ON facts(tx_id)")
    conn.commit()

    # Verify final schema
    final_cols = [r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()]
    print(f"\n✅ Migration complete: {len(final_cols)} columns")
    print(f"   Columns: {', '.join(final_cols)}")
    print("   Old table preserved as 'facts_old_32col' for safety")

    conn.close()


if __name__ == "__main__":
    if "--confirm" not in sys.argv:
        print("⚠️  DESTRUCTIVE MIGRATION: 32 → 21 columns")
        print("   Run with --confirm to execute")
        print(f"   DB: {DB_PATH}")
        sys.exit(0)
    migrate()
