# [C5-REAL] Exergy-Maximized
"""
cat_id: build-semantic-trees
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import asyncio
import os
import sys

import aiosqlite

# Ensure we can import cortex
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cortex.engine.logic.atms import AtmsAdapter


async def build_semantic_trees():
    print("Initiating Semantic Tree Build via ATMS in Rust (C5-REAL)...")
    db_path = os.environ.get("CORTEX_DB_PATH", os.path.expanduser("~/.cortex/cortex.db"))
    if not os.path.exists(db_path):
        print(f"Error: DB {db_path} not found.")
        sys.exit(1)

    try:
        atms = AtmsAdapter()
    except Exception as e:
        print(f"Error initializing ATMS: {e}")
        sys.exit(1)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        print("Fetching facts with fact_hash...")
        async with db.execute(
            "SELECT id, fact_hash FROM facts WHERE fact_hash IS NOT NULL AND is_tombstoned = 0"
        ) as cursor:
            facts = await cursor.fetchall()

        fact_hash_map = {}
        for f in facts:
            fact_hash = f["fact_hash"]
            if fact_hash:
                fact_hash_map[f["id"]] = fact_hash
                atms.add_node(fact_hash)

        print(f"Added {len(fact_hash_map)} nodes to ATMS Graph.")

        print("Fetching causal edges...")
        async with db.execute("SELECT fact_id, parent_id FROM causal_edges") as cursor:
            edges = await cursor.fetchall()

        added_edges = 0
        for e in edges:
            child_id = e["fact_id"]
            parent_id = e["parent_id"]
            if child_id in fact_hash_map and parent_id in fact_hash_map:
                atms.add_dependency(fact_hash_map[child_id], fact_hash_map[parent_id])
                added_edges += 1

        print(f"Added {added_edges} causal dependencies to ATMS Graph.")
        print("Semantic Trees construction via ATMS completed successfully.")


if __name__ == "__main__":
    asyncio.run(build_semantic_trees())
