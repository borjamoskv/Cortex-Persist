#!/usr/bin/env python3
"""A1 — Ledger Freeze & Snapshot.

Creates a forensic backup of the CORTEX ledger before re-anchor:
  - Full DB copy (cortex_pre_reanchor_YYYYMMDD.db)
  - JSONL exports of transactions, merkle_roots, integrity_checks
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".cortex" / "cortex.db"
SNAPSHOT_DIR = Path.home() / ".cortex" / "snapshots"


def snapshot(db_path: Path = DB_PATH) -> Path:
    """Create a timestamped snapshot of the CORTEX DB."""
    if not db_path.exists():
        print(f"❌ DB not found: {db_path}")
        sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Full DB copy
    dest = SNAPSHOT_DIR / f"cortex_pre_reanchor_{ts}.db"
    shutil.copy2(db_path, dest)
    print(f"✅ DB snapshot: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")

    # 2. JSONL exports
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    tables = ["transactions", "merkle_roots", "integrity_checks"]
    for table in tables:
        out = SNAPSHOT_DIR / f"{table}_{ts}.jsonl"
        cursor = conn.execute(f"SELECT * FROM {table} ORDER BY id")
        count = 0
        with open(out, "w") as f:
            for row in cursor:
                f.write(json.dumps(dict(row), default=str) + "\n")
                count += 1
        print(f"✅ Exported {table}: {count} rows → {out.name}")

    # 3. Summary stats
    cursor = conn.execute("SELECT COUNT(*) FROM transactions")
    tx_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT MIN(id), MAX(id) FROM transactions")
    tx_range = cursor.fetchone()
    cursor = conn.execute("SELECT COUNT(*) FROM merkle_roots")
    mr_count = cursor.fetchone()[0]

    conn.close()

    print("\n📊 Summary:")
    print(f"   Transactions: {tx_count} (ID range: {tx_range[0]}–{tx_range[1]})")
    print(f"   Merkle Roots: {mr_count}")
    print(f"   Snapshot dir: {SNAPSHOT_DIR}")
    return dest


if __name__ == "__main__":
    snapshot()
