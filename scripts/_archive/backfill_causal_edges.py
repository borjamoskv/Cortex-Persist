"""Backfill causal_edges from parent_decision_id stored in encrypted meta.

Reads all facts, decrypts meta, extracts parent_decision_id, and creates
derived_from edges in causal_edges for any fact that has a parent but
no existing edge.

Usage:
    python scripts/backfill_causal_edges.py [--dry-run]
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill_causal_edges")

DB_PATH = os.environ.get(
    "CORTEX_DB_PATH",
    os.path.expanduser("~/.cortex/cortex.db"),
)

EDGE_TYPE = "derived_from"


def backfill(dry_run: bool = False) -> dict[str, int]:
    """Backfill causal edges from parent_decision_id in meta."""
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()
    conn = sqlite3.connect(DB_PATH)

    # Ensure causal_edges table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS causal_edges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id     INTEGER NOT NULL,
            parent_id   INTEGER,
            signal_id   INTEGER,
            edge_type   TEXT NOT NULL DEFAULT 'triggered_by',
            project     TEXT,
            tenant_id   TEXT NOT NULL DEFAULT 'default',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (fact_id) REFERENCES facts(id)
        )
    """)
    conn.commit()

    # Get all facts with their meta
    rows = conn.execute("SELECT id, meta, project, tenant_id FROM facts").fetchall()

    stats = {
        "total_facts": len(rows),
        "with_parent": 0,
        "edges_created": 0,
        "already_linked": 0,
        "decrypt_errors": 0,
        "invalid_parent": 0,
    }

    # Build set of existing edges for O(1) lookup
    existing = set()
    edge_rows = conn.execute("SELECT fact_id, parent_id FROM causal_edges").fetchall()
    for er in edge_rows:
        existing.add((er[0], er[1]))

    # Build set of valid fact IDs for FK validation
    valid_ids = {r[0] for r in conn.execute("SELECT id FROM facts").fetchall()}

    batch: list[tuple[int, int, str, str, str]] = []

    for fact_id, encrypted_meta, project, tenant_id in rows:
        parent_id: int | None = None
        tid = tenant_id or "default"

        # Source 1: parent_decision_id column (most reliable)
        col_row = conn.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
        if col_row and col_row[0]:
            parent_id = int(col_row[0])

        # Source 2: encrypted meta (fallback)
        if parent_id is None and encrypted_meta:
            try:
                meta_str = enc.decrypt_str(encrypted_meta, tenant_id=tid)
                meta = json.loads(meta_str)
                pdi = meta.get("parent_decision_id")
                if pdi:
                    parent_id = int(pdi)
            except Exception:
                try:
                    meta = json.loads(encrypted_meta)
                    pdi = meta.get("parent_decision_id")
                    if pdi:
                        parent_id = int(pdi)
                except (json.JSONDecodeError, TypeError):
                    stats["decrypt_errors"] += 1

        if not parent_id:
            continue

        stats["with_parent"] += 1

        # Validate parent exists
        if parent_id not in valid_ids:
            stats["invalid_parent"] += 1
            continue

        # Check if edge already exists
        if (fact_id, parent_id) in existing:
            stats["already_linked"] += 1
            continue

        batch.append(
            (
                fact_id,
                parent_id,
                EDGE_TYPE,
                project or "unknown",
                tid,
            )
        )
        existing.add((fact_id, parent_id))

    if batch and not dry_run:
        conn.executemany(
            "INSERT INTO causal_edges "
            "(fact_id, parent_id, edge_type, project, tenant_id) "
            "VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        conn.commit()

    stats["edges_created"] = len(batch)

    # Final count
    final_count = conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0]
    stats["total_edges_after"] = final_count

    conn.close()
    return stats


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("DRY RUN — no edges will be written")

    logger.info("DB: %s", DB_PATH)
    stats = backfill(dry_run=dry_run)

    logger.info("═══ Backfill Results ═══")
    logger.info("Total facts scanned:   %d", stats["total_facts"])
    logger.info("Facts with parent_id:  %d", stats["with_parent"])
    logger.info("Edges created:         %d", stats["edges_created"])
    logger.info("Already linked:        %d", stats["already_linked"])
    logger.info("Invalid parent refs:   %d", stats["invalid_parent"])
    logger.info("Decrypt errors:        %d", stats["decrypt_errors"])
    logger.info("Total edges now:       %d", stats["total_edges_after"])

    density = stats["total_edges_after"] / stats["total_facts"] if stats["total_facts"] > 0 else 0
    logger.info(
        "Edge density:          %.1f%% (%d/%d)",
        density * 100,
        stats["total_edges_after"],
        stats["total_facts"],
    )


if __name__ == "__main__":
    main()
