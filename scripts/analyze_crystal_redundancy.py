"""
Script to analyze crystal redundancy (entropy) in the CORTEX database.

This tool acts as a dry-run for the NightShift Phase 3: Semantic Merger (Ω₂).
It calculates the cosine similarity between all pairs of crystals in the same
project and reports those that exceed the merging threshold (0.92).
"""

import argparse
import logging
import sqlite3
import sys
from typing import NamedTuple

import numpy as np

from cortex.extensions.swarm.crystal_thermometer import calculate_resonance

logger = logging.getLogger("analyze_redundancy")

MERGE_THRESHOLD = 0.92


class ScannedCrystal(NamedTuple):
    fact_id: str
    project: str
    content: str
    vector: np.ndarray


def load_crystals(conn: sqlite3.Connection) -> list[ScannedCrystal]:
    """Load all crystals and their embeddings from the database."""
    query = """
        SELECT
            m.id,
            m.project_id,
            m.content,
            v.embedding
        FROM facts_meta m
        JOIN vec_facts v ON m.id = v.id
        WHERE v.embedding IS NOT NULL
    """
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()

        crystals = []
        for rowId, project, content, emb_blob in rows:
            if not emb_blob:
                continue
            emb_array = np.frombuffer(emb_blob, dtype=np.float32)
            crystals.append(
                ScannedCrystal(
                    fact_id=str(rowId), project=project, content=content, vector=emb_array
                )
            )
        return crystals
    except Exception as e:
        logger.error(f"Failed to load crystals: {e}")
        return []


def analyze_redundancy(
    crystals: list[ScannedCrystal],
) -> list[tuple[ScannedCrystal, ScannedCrystal, float]]:
    """Identify pairs of crystals that are highly redundant."""
    logger.info(f"Analyzing {len(crystals)} crystals for redundancy...")

    proposed_merges = []

    # We only compare crystals within the same project
    crystals_by_project = {}
    for c in crystals:
        crystals_by_project.setdefault(c.project, []).append(c)

    for _project, proj_crystals in crystals_by_project.items():
        n = len(proj_crystals)
        if n < 2:
            continue

        for i in range(n):
            for j in range(i + 1, n):
                c1 = proj_crystals[i]
                c2 = proj_crystals[j]

                # Use the existing temperature resonance function which calculates cosine similarity
                similarity = calculate_resonance(c1.vector, c2.vector)

                if similarity >= MERGE_THRESHOLD:
                    proposed_merges.append((c1, c2, similarity))

    return proposed_merges


def main():
    parser = argparse.ArgumentParser(description="Analyze CORTEX database for crystal redundancy.")
    parser.add_argument(
        "--db-path",
        type=str,
        default="/Users/borjafernandezangulo/.cortex/cortex.db",
        help="Path to the cortex.db file",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        db = sqlite3.connect(args.db_path)
    except Exception as e:
        logger.error(f"Failed to connect to database at {args.db_path}: {e}")
        sys.exit(1)

    crystals = load_crystals(db)
    if not crystals:
        logger.warning("No crystals with embeddings found in the database. Exiting.")
        sys.exit(0)

    proposed_merges = analyze_redundancy(crystals)

    print("\n" + "=" * 80)
    print(" NIGHTSHIFT SEMANTIC MERGER (Ω₂) DRY-RUN ")
    print("=" * 80)
    print(f" Total Crystals Scanned : {len(crystals)}")
    print(f" Merge Threshold        : {MERGE_THRESHOLD}")
    print(f" Proposed Merges Found  : {len(proposed_merges)}")
    print("=" * 80 + "\n")

    if proposed_merges:
        # Sort by highest similarity first
        proposed_merges.sort(key=lambda x: x[2], reverse=True)

        for idx, (c1, c2, sim) in enumerate(proposed_merges, 1):
            print(f"[{idx}] ⚠️ HIGH REDUNDANCY IDENTIFIED — SIMILARITY: {sim:.3f}")
            print(f"    Project: {c1.project}")
            print(f"    Crystal 1 (ID: {c1.fact_id}):")
            prefix1 = (
                c1.content[:80].replace("\n", " ") + "..."
                if len(c1.content) > 80
                else c1.content.replace("\n", " ")
            )
            print(f'        "{prefix1}"')
            print(f"    Crystal 2 (ID: {c2.fact_id}):")
            prefix2 = (
                c2.content[:80].replace("\n", " ") + "..."
                if len(c2.content) > 80
                else c2.content.replace("\n", " ")
            )
            print(f'        "{prefix2}"')
            print("-" * 80)

        print("\nThese crystals would be fused by LLM synthesis during a live NightShift cycle.")
    else:
        print("✅ System entropy is low. No highly redundant crystals found.")


if __name__ == "__main__":
    main()
