#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Ouroboros FTS5 Optimization Maintenance Script

Optimizes SQLite FTS5 search indexes by running the 'optimize' command.
This merges internal b-trees to maintain fast read queries and reduce index size.
Recommended to run periodically via cron (e.g. daily or weekly).
"""

import argparse
import logging
import sqlite3
from pathlib import Path

from cortex.database.core import connect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fts_optimize")

FTS_TABLES = [
    "facts_fts",
    "facts_meta_fts",
    "episodes_fts"
]

def optimize_fts(db_path: str):
    db_file = Path(db_path).expanduser()
    if not db_file.exists():
        logger.error(f"Database not found at {db_file}")
        return

    logger.info("Igniting FTS5 Index Optimization...")
    
    # Use hardened CORTEX synchronous connection
    try:
        with connect(str(db_file)) as conn:
            cursor = conn.cursor()
            
            for table in FTS_TABLES:
                logger.info(f"Checking FTS5 table: {table}")
                try:
                    # Verify if table exists before optimizing
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if cursor.fetchone():
                        logger.info(f"Optimizing FTS5 table: {table}")
                        cursor.execute(f"INSERT INTO {table}({table}) VALUES('optimize')")
                        conn.commit()
                        logger.info(f"[OK] {table} optimized.")
                    else:
                        logger.debug(f"FTS5 table {table} does not exist. Skipping.")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Failed to optimize {table}: {e}")
                    
        logger.info("FTS5 Optimization Complete. Search operations will now operate at peak thermodynamic efficiency.")
    except Exception as e:
        logger.error(f"Failed to execute optimization: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize FTS5 Search Indexes")
    parser.add_argument(
        "--db",
        type=str,
        default="~/.cortex/cortex.db",
        help="Path to Cortex database",
    )
    args = parser.parse_args()
    optimize_fts(args.db)
