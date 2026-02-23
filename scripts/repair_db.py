import os
import sqlite3

db_path = os.path.expanduser("~/.cortex/cortex.db")

# List of tables that SHOULD have tenant_id according to schema.py
tables_with_tenants = [
    "facts",
    "sessions",
    "transactions",
    "heartbeats",
    "time_entries",
    "agents",
    "ghosts",
    "compaction_log",
    "context_snapshots",
    "episodes"
]


def repair():
    """Repair the database by adding missing tenant_id columns and indices."""
    conn = sqlite3.connect(db_path)
    try:
        for table in tables_with_tenants:
            # Check if table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                f"WHERE type='table' AND name='{table}'"
            )
            if not cursor.fetchone():
                print(f"Table {table} does not exist, skipping.")
                continue

            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            if "tenant_id" not in columns:
                print(f"Adding tenant_id to {table}...")
                conn.execute(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                )

        # Also check for idx_tx_tenant if it was missing
        print("Ensuring indices...")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tx_tenant ON transactions(tenant_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_tenant ON episodes(tenant_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ctx_snap_tenant "
            "ON context_snapshots(tenant_id)"
        )

        conn.commit()
        print("Full repair complete.")
    except Exception as e:
        print(f"Repair failed: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    repair()
