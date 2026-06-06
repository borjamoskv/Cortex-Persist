#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Ouroboros Temporal Pruning Daemon.

Executes thermal purges on the CORTEX Knowledge Graph based on the
decay_half_life of each fact. Facts whose temporal decay falls below
the minimum viability threshold (e.g., 3 half-lives / 12.5% exergy)
are autonomously tombstoned.

Axiom: Ω2 (Entropic Asymmetry)
"""

import logging
import sqlite3
from pathlib import Path

# Minimum Exergy Threshold (3 half-lives = 0.125)
MIN_EXERGY_THRESHOLD = 0.125

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ouroboros_prune")


def execute_thermal_purge(db_path: str = "~/.cortex/cortex.db") -> None:
    """Scan facts and tombstone those that have decayed past the threshold."""
    db_file = Path(db_path).expanduser()
    if not db_file.exists():
        logger.error(f"Database not found at {db_file}")
        return

    logger.info("Igniting Ouroboros Thermal Purge...")
    try:
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # We calculate decay in SQL:
            # age_days = (now - created_at) / 86400.0
            # decay_factor = 0.5 ^ (age_days / decay_half_life)

            # Identify candidates
            # Only prune non-diamond facts that are not already tombstoned
            sql_find = """
                SELECT id, content, created_at, decay_half_life,
                       ((strftime('%s', 'now') - strftime('%s', created_at)) / 86400.0) as age_days
                FROM facts
                WHERE is_diamond = 0 AND is_tombstoned = 0
            """
            cursor.execute(sql_find)
            rows = cursor.fetchall()

            purged_count = 0
            for row in rows:
                age_days = float(row["age_days"])
                half_life = float(row["decay_half_life"]) if row["decay_half_life"] else 30.0

                # Math: decay = 0.5 ^ (age / half_life)
                if half_life <= 0:
                    decay = 0.0
                else:
                    decay = 0.5 ** (age_days / half_life)

                if decay < MIN_EXERGY_THRESHOLD:
                    # Tombstone the fact
                    logger.info(
                        f"Thermal Death: Fact {row['id']} (Age: {age_days:.1f}d, Half-Life: {half_life:.1f}d, Exergy: {decay:.3f})"
                    )
                    cursor.execute(
                        "UPDATE facts SET is_tombstoned = 1, updated_at = datetime('now') WHERE id = ?",
                        (row["id"],),
                    )
                    purged_count += 1

            conn.commit()
            logger.info(f"Ouroboros Cycle Complete. {purged_count} facts returned to the void.")

    except sqlite3.Error as e:
        logger.error(f"Ouroboros encountered a temporal distortion: {e}")


if __name__ == "__main__":
    execute_thermal_purge()
