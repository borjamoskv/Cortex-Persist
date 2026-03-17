import os
import sqlite3
import sys

# Append CORTEX path to resolve imports if necessary
sys.path.insert(0, os.path.expanduser("~/30_CORTEX"))

from cortex.engine.store_validators import normalize_project

DB_PATH = os.path.expanduser("~/.cortex/cortex.db")

OVERRIDES = {
    "borjamoskv/Cortex-Persist": "CORTEX_PERSIST",
    "autodidact_ingestion": "AUTODIDACT",
}


def clean_project_name(raw: str) -> str:
    if raw in OVERRIDES:
        return OVERRIDES[raw]
    return normalize_project(raw)


def main():
    conn = sqlite3.connect(DB_PATH)

    print("--- CORTEX Database Cleanup & Normalization ---")

    # 1. Purge Tombstoned Records (Zero-Entropy directive)
    print("\n1. Purging tombstoned facts...")
    cursor = conn.execute("DELETE FROM facts WHERE is_tombstoned = 1")
    print(f"  Deleted {cursor.rowcount} tombstoned facts.")

    # 2. Cleanup orphaned facts_fts
    print("\n2. Cleaning orphaned FTS records...")
    cursor = conn.execute("DELETE FROM facts_fts WHERE rowid NOT IN (SELECT id FROM facts)")
    print(f"  Deleted {cursor.rowcount} FTS orphans.")

    # 3. Cleanup orphaned causal_edges
    print("\n3. Cleaning orphaned causal edges...")
    cursor = conn.execute(
        "DELETE FROM causal_edges WHERE fact_id NOT IN (SELECT id FROM facts) OR (parent_id IS NOT NULL AND parent_id NOT IN (SELECT id FROM facts))"
    )
    print(f"  Deleted {cursor.rowcount} causal edge orphans.")

    # 4. Cleanup orphaned parent_decision_id
    print("\n4. Clearing orphaned parent_decision_id in facts (Schema Ghosts)...")
    try:
        cursor = conn.execute(
            "UPDATE facts SET parent_decision_id = NULL WHERE parent_decision_id IS NOT NULL AND parent_decision_id NOT IN (SELECT id FROM facts)"
        )
        print(f"  Cleared {cursor.rowcount} orphaned parent_decision_id references.")
    except sqlite3.OperationalError as e:
        # Just in case parent_decision_id was removed in a migration
        print(f"  Skipped parent_decision_id cleanup: {e}")

    # 5. Project Harmonization
    print("\n5. Harmonizing project names...")
    cursor = conn.execute("SELECT DISTINCT project FROM facts")
    projects = [row[0] for row in cursor.fetchall() if row[0]]

    updates = 0
    for proj in projects:
        norm = clean_project_name(proj)
        if norm != proj:
            print(f"  Translating: {proj} -> {norm}")
            conn.execute("UPDATE facts SET project = ? WHERE project = ?", (norm, proj))
            conn.execute("UPDATE causal_edges SET project = ? WHERE project = ?", (norm, proj))
            conn.execute("UPDATE facts_fts SET project = ? WHERE project = ?", (norm, proj))
            updates += 1

    print(f"  Harmonized {updates} project namespaces.")

    # Additional cleanup on orphaned/non-matching project strings in FTS or edges
    # (Just in case they weren't linked to an existing fact but weren't fully deleted)
    conn.execute(
        "UPDATE causal_edges SET project = (SELECT project FROM facts WHERE facts.id = causal_edges.fact_id) WHERE project != (SELECT project FROM facts WHERE facts.id = causal_edges.fact_id)"
    )

    # 6. Check quarantined/source-less
    print("\n6. Final Audit...")
    cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE is_quarantined = 1")
    q_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE source IS NULL OR source = ''")
    s_count = cursor.fetchone()[0]

    print(f"  Quarantined facts remaining: {q_count}")
    print(f"  Source-less facts remaining: {s_count}")

    print("\nCommitting changes...")
    conn.commit()
    conn.close()
    print("Done. Entropy reduced.")


if __name__ == "__main__":
    main()
