import os
import shutil
import sqlite3

DB_PATH = os.path.expanduser("~/.cortex/cortex.db")
PERSONAL_DB_PATH = os.path.expanduser("~/.cortex/personal_memories.db")
COLD_DB_PATH = os.path.expanduser("~/.cortex/cold_storage.db")

# Repatriated to PERSONAL
PERSONAL_PROJECTS = [
    "borja.moskv.eth",
    "borjamoskv",
    "borjamoskv.com",
    "el-pueblo-online",
    "filete-cumbia",
    "garmin-dashboard",
    "xokas-elevator",
    "gordacorp",
    "millennium",
    "noir-ui-kit",
    "openclaw",
    "reddit_overlord",
    "songlines-manifestation-immunity",
    "sonic-supreme",
    "sonic_sovereign",
    "SonicNotch",
    "veo-lyria-studio",
    "lyria-studio",
    "NAROA",
    "LIVENOTCH",
    "eqmac-re",
    "comienzos-clone",
    "conspiracy-calculator",
    "FrontierApp",
    "impact-web",
    "manteca-web",
    "moskvbot",
    "moskvbot-test",
    "OLA3",
    "omni-translate",
    "raft-immunity",
]

# Repatriated to COLD STORAGE (Junk/Tests)
COLD_PROJECTS = [
    "test",
    "test-project",
    "test-integration-real",
    "test_lateral_inhibition",
    "testing",
    "test-integration",
    "test-vec",
    "vec-test",
    "default",
    "other-project",
    "blue",
    "temp",
    "cortex-test",
    "swarm-demo",
]


def ensure_db_copy(src, dest):
    """Creates a copy of the database structure (without virtual tables if they fail)"""
    if not os.path.exists(dest):
        print(f"Creating {dest} from {src} structure...")
        shutil.copy2(src, dest)
        # Clear data from the copy to start fresh
        conn = sqlite3.connect(dest)
        cursor = conn.cursor()
        # Remove triggers to allow clearing structure
        cursor.execute("DROP TRIGGER IF EXISTS prevent_tx_update")
        cursor.execute("DROP TRIGGER IF EXISTS prevent_tx_delete")

        # Only clear tables we care about (others should be system-wide)
        tables_to_clear = [
            "facts",
            "episodes",
            "transactions",
            "entities",
            "entity_relations",
            "entity_events",
            "memory_events",
        ]
        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError as e:
                print(f"Skipping table {table}: {e}")
        conn.commit()
        conn.close()


def move_project_data(project_name, src_conn, dest_path):
    print(f"Moving project: {project_name} -> {os.path.basename(dest_path)}")
    dest_conn = sqlite3.connect(dest_path)

    # We use a transaction context
    try:
        # 1. Facts
        facts = src_conn.execute(
            "SELECT * FROM facts WHERE project = ?", (project_name,)
        ).fetchall()
        if facts:
            columns = [d[0] for d in src_conn.execute("SELECT * FROM facts LIMIT 1").description]
            placeholders = ",".join(["?"] * len(columns))
            dest_conn.executemany(
                f"INSERT OR IGNORE INTO facts ({','.join(columns)}) VALUES ({placeholders})", facts
            )
            src_conn.execute("DELETE FROM facts WHERE project = ?", (project_name,))

        # 2. Episodes
        episodes = src_conn.execute(
            "SELECT * FROM episodes WHERE project = ?", (project_name,)
        ).fetchall()
        if episodes:
            columns = [d[0] for d in src_conn.execute("SELECT * FROM episodes LIMIT 1").description]
            placeholders = ",".join(["?"] * len(columns))
            dest_conn.executemany(
                f"INSERT OR IGNORE INTO episodes ({','.join(columns)}) VALUES ({placeholders})",
                episodes,
            )
            src_conn.execute("DELETE FROM episodes WHERE project = ?", (project_name,))

        # 3. Transactions (linked to these projects)
        txs = src_conn.execute(
            "SELECT * FROM transactions WHERE project = ?", (project_name,)
        ).fetchall()
        if txs:
            columns = [
                d[0] for d in src_conn.execute("SELECT * FROM transactions LIMIT 1").description
            ]
            placeholders = ",".join(["?"] * len(columns))
            dest_conn.executemany(
                f"INSERT OR IGNORE INTO transactions ({','.join(columns)}) VALUES ({placeholders})",
                txs,
            )
            # Remove triggers temporarily if they block Delete (they do)
            src_conn.execute("DROP TRIGGER IF EXISTS prevent_tx_update")
            src_conn.execute("DROP TRIGGER IF EXISTS prevent_tx_delete")
            src_conn.execute("DELETE FROM transactions WHERE project = ?", (project_name,))
            # We don't restore them yet, we'll do it at the end if needed (they'll be in the backup)

        dest_conn.commit()
    finally:
        dest_conn.close()


def main():
    import sys

    force = "--force" in sys.argv

    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    if not force:
        print("⚠️  WARNING: This script will DELETE data from the main CORTEX database.")
        print(f"   Source: {DB_PATH}")
        print(f"   Projects to move: {len(PERSONAL_PROJECTS)} personal + {len(COLD_PROJECTS)} cold")
        confirm = input("   Type 'YES' to proceed: ")
        if confirm != "YES":
            print("Aborted.")
            return

    ensure_db_copy(DB_PATH, PERSONAL_DB_PATH)
    ensure_db_copy(DB_PATH, COLD_DB_PATH)

    src_conn = sqlite3.connect(DB_PATH)
    try:
        # Disable triggers in CORTEX (main) to allow cleanup
        src_conn.execute("DROP TRIGGER IF EXISTS prevent_tx_update")
        src_conn.execute("DROP TRIGGER IF EXISTS prevent_tx_delete")

        for project in PERSONAL_PROJECTS:
            move_project_data(project, src_conn, PERSONAL_DB_PATH)

        for project in COLD_PROJECTS:
            move_project_data(project, src_conn, COLD_DB_PATH)

        src_conn.commit()
        print("Vacuuming main database...")
        src_conn.execute("VACUUM")
        print("Success. Context has been repatriated.")
    except Exception as e:
        print(f"Error: {e}")
        src_conn.rollback()
    finally:
        src_conn.close()


if __name__ == "__main__":
    main()
