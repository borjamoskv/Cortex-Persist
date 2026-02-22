"""Purge garbage facts from CORTEX database.

One-shot script to clean ~200 garbage entries identified by audit.
Creates a backup before any destructive operation.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".cortex" / "cortex.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.backup-pre-purge")


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"✗ Database not found: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def backup() -> None:
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✓ Backup created: {BACKUP_PATH}")


def purge_by_query(
    conn: sqlite3.Connection, label: str, query: str, params: tuple = ()
) -> int:
    cursor = conn.execute(query, params)
    count = cursor.rowcount
    if count > 0:
        print(f"  🗑  {label}: {count} facts deleted")
    return count


def fix_by_query(
    conn: sqlite3.Connection, label: str, query: str, params: tuple = ()
) -> int:
    cursor = conn.execute(query, params)
    count = cursor.rowcount
    if count > 0:
        print(f"  🔧 {label}: {count} facts fixed")
    return count


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS index after deleting rows."""
    try:
        conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")
        print("  ✓ FTS index rebuilt")
    except sqlite3.OperationalError as e:
        print(f"  ⚠ FTS rebuild skipped: {e}")


def main() -> None:
    print("=" * 60)
    print("CORTEX Garbage Purge")
    print("=" * 60)

    backup()

    conn = connect()
    total_deleted = 0
    total_fixed = 0

    print("\n--- Phase 1: Delete garbage facts ---")

    # 1. tenant1 test data ("Fact from T1")
    total_deleted += purge_by_query(
        conn,
        "tenant1 test data",
        "DELETE FROM facts WHERE project = 'tenant1'",
    )

    # 2. debug test artifact
    total_deleted += purge_by_query(
        conn,
        "debug test artifacts",
        "DELETE FROM facts WHERE project = 'debug'",
    )

    # 3. Empty bridges (no source/target/pattern)
    total_deleted += purge_by_query(
        conn,
        "Empty bridges",
        "DELETE FROM facts WHERE fact_type = 'bridge' AND "
        "(content LIKE 'BRIDGE:  →%' OR content LIKE 'BRIDGE: agent:moskv-1 →  |%')",
    )

    # 4. Empty error templates
    total_deleted += purge_by_query(
        conn,
        "Empty error templates",
        "DELETE FROM facts WHERE content LIKE 'ERROR:  | CAUSA:  | FIX:%'",
    )

    # 5. Empty ghost templates
    total_deleted += purge_by_query(
        conn,
        "Empty ghost templates (other-project)",
        "DELETE FROM facts WHERE content LIKE 'GHOST: other-project | Última tarea: desconocida%'",
    )

    # 6. Secret code test data
    total_deleted += purge_by_query(
        conn,
        "Secret code test data",
        "DELETE FROM facts WHERE content LIKE 'The secret code for the audit is:%'",
    )

    # 7. Duplicate API key errors — keep oldest, delete rest
    rows = conn.execute(
        "SELECT id FROM facts WHERE content LIKE "
        "'Error code: 401 - {%error%:%message%:%API Key%' "
        "ORDER BY id ASC"
    ).fetchall()
    if len(rows) > 1:
        ids_to_delete = [r[0] for r in rows[1:]]
        placeholders = ",".join("?" * len(ids_to_delete))
        total_deleted += purge_by_query(
            conn,
            "Duplicate API key errors",
            f"DELETE FROM facts WHERE id IN ({placeholders})",
            tuple(ids_to_delete),
        )

    # 8. swarm mission duplicates
    rows = conn.execute(
        "SELECT content, MIN(id) as keep_id, COUNT(*) as cnt "
        "FROM facts WHERE content LIKE 'Mission M-%' "
        "GROUP BY content HAVING cnt > 1"
    ).fetchall()
    for content, keep_id, _cnt in rows:
        total_deleted += purge_by_query(
            conn,
            f"Duplicate missions (kept #{keep_id})",
            "DELETE FROM facts WHERE content = ? AND id != ?",
            (content, keep_id),
        )

    # 9. General exact duplicates (same content, keep oldest per project)
    rows = conn.execute(
        "SELECT content, project, MIN(id) as keep_id, COUNT(*) as cnt "
        "FROM facts "
        "GROUP BY content, project HAVING cnt > 1"
    ).fetchall()
    for content, project, keep_id, _cnt in rows:
        total_deleted += purge_by_query(
            conn,
            f"Exact dups in {project} (kept #{keep_id})",
            "DELETE FROM facts WHERE content = ? AND project = ? AND id != ?",
            (content, project, keep_id),
        )

    print("\n--- Phase 2: Fix malformed facts ---")

    # 10. Double-prefixed decisions: "DECISION: DECISION: X" → "DECISION: X"
    total_fixed += fix_by_query(
        conn,
        "Double-prefixed DECISION:",
        "UPDATE facts SET content = REPLACE(content, 'DECISION: DECISION:', 'DECISION:') "
        "WHERE content LIKE 'DECISION: DECISION:%'",
    )

    # 11. Double-suffixed RAZON: " | RAZON:  | RAZON:" → " | RAZON:"
    total_fixed += fix_by_query(
        conn,
        "Double-suffixed RAZON:",
        "UPDATE facts SET content = REPLACE(content, ' | RAZON:  | RAZON:', ' | RAZON:') "
        "WHERE content LIKE '% | RAZON:  | RAZON:%'",
    )

    # 12. Trailing empty " | RAZON: " → strip trailing whitespace
    total_fixed += fix_by_query(
        conn,
        "Empty RAZON suffix",
        "UPDATE facts SET content = REPLACE(content, ' | RAZON: ', '') "
        "WHERE content LIKE '% | RAZON: ' AND content NOT LIKE '% | RAZON: %_'",
    )

    print("\n--- Phase 3: Rebuild indexes ---")
    rebuild_fts(conn)

    conn.commit()

    # Final stats
    remaining = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()

    print(f"\n{'=' * 60}")
    print("RESULTS:")
    print(f"  Deleted: {total_deleted} facts")
    print(f"  Fixed:   {total_fixed} facts")
    print(f"  Remaining: {remaining} facts")
    print(f"  Backup at: {BACKUP_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
