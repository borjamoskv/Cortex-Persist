#!/usr/bin/env python3
"""
CORTEX EXPANSE v4.3 - Purge Projects (Facts Table)
Consolidates all projects with < 5 facts or older than 30 days into `ARCHIVE_MISC`.
"""

import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("~/.cortex/cortex.db").expanduser()
ARCHIVE_PROJECT = "ARCHIVE_MISC"
PROTECTED_PROJECTS = {ARCHIVE_PROJECT, "GLOBAL", "SYSTEM", "CORTEX", "MOSKV"}

def run_purge(dry_run: bool = True):
    print(f"--- CORTEX GREAT PURGE {'[DRY RUN]' if dry_run else '[EXECUTION]'} ---")
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project, count(*) as fact_count, max(created_at) as last_updated
        FROM facts
        WHERE valid_until IS NULL
        GROUP BY project
    """)
    projects = cursor.fetchall()
    
    now = datetime.now(timezone.utc).timestamp()
    to_archive = []

    for p in projects:
        pid = p["project"]
        count = p["fact_count"]
        # created_at is TEXT like '2023-10-10 10:10:10' or '2023-10-10T10:10:10Z'
        last_updated_str = p["last_updated"]
        
        try:
            # Handle different ISO formats
            if 'T' in last_updated_str:
                dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            last_updated = dt.timestamp()
        except Exception:
            last_updated = 0

        age_days = (now - last_updated) / 86400.0 if last_updated else 999

        if pid in PROTECTED_PROJECTS or pid.upper() in PROTECTED_PROJECTS or pid.startswith("ARCHIVE_"):
            continue

        if count < 5 or age_days > 30:
            to_archive.append({"pid": pid, "count": count, "age": age_days})

    print(f"Found {len(to_archive)} projects to consolidate into {ARCHIVE_PROJECT}.")
    
    for p in to_archive:
        print(f" -> {p['pid']} (Facts: {p['count']}, Age: {p['age']:.1f} days)")

    if not dry_run:
        pids = [p["pid"] for p in to_archive]
        if pids:
            placeholders = ",".join("?" * len(pids))
            cursor.execute(
                f"UPDATE facts SET project = ? WHERE project IN ({placeholders})",
                [ARCHIVE_PROJECT] + pids
            )
            conn.commit()
            print(f"\nSUCCESS: Moved facts from {len(pids)} projects to {ARCHIVE_PROJECT}.")
        else:
            print("\nNo projects need archiving.")
    else:
        print("\nSkipping DB update (Dry Run). Run with --execute to apply.")

    conn.close()

if __name__ == "__main__":
    import sys
    dry = "--execute" not in sys.argv
    run_purge(dry_run=dry)
