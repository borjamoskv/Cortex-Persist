#!/usr/bin/env python3
"""
migrate_project_normalization.py — Tier 2 Confluence Resolution.

Backfills existing facts to canonical UPPER_SNAKE_CASE project names.
Safe: fact hash (SHA-256 of content only) is NOT affected by project field.
FTS5 content synced via `INSERT INTO facts_fts(facts_fts) VALUES('rebuild')`.

Usage:
    python3 scripts/migrate_project_normalization.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone

ALIASES: dict[str, str] = {
    "cortex": "CORTEX",
    "Cortex-Persist": "CORTEX_PERSIST",
    "CORTEX-Persist": "CORTEX_PERSIST",
    "cortex-persist": "CORTEX_PERSIST",
    "system": "SYSTEM",
    "global": "GLOBAL",
    "Aether": "AETHER",
    "cortex-core": "CORTEX_CORE",
}

DB_PATH = "/Users/borjafernandezangulo/.cortex/cortex.db"


def run(dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    total_updated = 0
    report: list[str] = []

    try:
        conn.execute("BEGIN")

        for raw, canonical in ALIASES.items():
            if raw == canonical:
                continue

            # ── facts ────────────────────────────────────────────────────
            count = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE project = ?", (raw,)
            ).fetchone()[0]
            if count > 0:
                report.append(f"  facts        : '{raw}' → '{canonical}' ({count} rows)")
                if not dry_run:
                    conn.execute(
                        "UPDATE facts SET project = ?, updated_at = ? WHERE project = ?",
                        (canonical, now, raw),
                    )
                total_updated += count

            # ── causal_edges ─────────────────────────────────────────────
            ce_count = conn.execute(
                "SELECT COUNT(*) FROM causal_edges WHERE project = ?", (raw,)
            ).fetchone()[0]
            if ce_count > 0:
                report.append(f"  causal_edges : '{raw}' → '{canonical}' ({ce_count} rows)")
                if not dry_run:
                    conn.execute(
                        "UPDATE causal_edges SET project = ? WHERE project = ?",
                        (canonical, raw),
                    )

        # ── FTS5 rebuild (syncs project col from facts table) ────────────
        # Must happen after all facts updates, in same transaction.
        if not dry_run and total_updated > 0:
            report.append("  facts_fts    : full rebuild triggered")
            conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")

        if dry_run:
            conn.execute("ROLLBACK")
            print("[DRY-RUN] No changes written. Preview:")
        else:
            conn.execute("COMMIT")
            print(f"[COMMIT] Migration applied at {now}")

        for line in report:
            print(line)
        print(f"\nTotal fact rows affected: {total_updated}")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"[ROLLBACK] Error: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize project names in CORTEX DB.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
