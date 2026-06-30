# [C5-REAL] Exergy-Maximized
"""
Autonomic Data Escape Hatch (Dead Man Switch).
Secures flat data export capability under long-term system inoperability.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("babylon60.ledger.escape_hatch")

LIVENESS_KEY = "escape_hatch_last_liveness"


async def record_liveness(conn: aiosqlite.Connection) -> None:
    """Updates the liveness token in cortex_meta."""
    now_str = datetime.now(timezone.utc).isoformat()
    # Ensure cortex_meta exists before writing
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS cortex_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
    )
    await conn.execute(
        "INSERT OR REPLACE INTO cortex_meta (key, value) VALUES (?, ?);",
        (LIVENESS_KEY, now_str),
    )
    await conn.commit()
    logger.info("Liveness recorded: %s", now_str)


def record_liveness_sync(db_path: str | Path) -> None:
    """Updates the liveness token in cortex_meta (synchronous)."""
    import sqlite3

    now_str = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cortex_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            )
            conn.execute(
                "INSERT OR REPLACE INTO cortex_meta (key, value) VALUES (?, ?);",
                (LIVENESS_KEY, now_str),
            )
            conn.commit()
            logger.info("Liveness recorded (sync): %s", now_str)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to record sync liveness at %s: %s", db_path, e)


async def is_dead_man_switch_triggered(
    conn: aiosqlite.Connection, threshold_days: int = 30
) -> bool:
    """Checks if the elapsed time since last liveness is greater than threshold_days."""
    # Check if table exists first
    cursor_table = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cortex_meta';"
    )
    if not await cursor_table.fetchone():
        logger.warning("cortex_meta table missing. Triggering escape hatch by default.")
        return True

    cursor = await conn.execute("SELECT value FROM cortex_meta WHERE key = ?;", (LIVENESS_KEY,))
    row = await cursor.fetchone()
    if not row:
        logger.warning("No liveness record found. Triggering escape hatch by default.")
        return True

    last_liveness_str = row[0]
    try:
        last_liveness = datetime.fromisoformat(last_liveness_str)
    except ValueError:
        logger.error(
            "Corrupted liveness timestamp: %s. Triggering escape hatch.", last_liveness_str
        )
        return True

    delta = datetime.now(timezone.utc) - last_liveness
    if delta.days >= threshold_days:
        logger.critical(
            "Dead man switch triggered! Inactivity days: %d >= %d", delta.days, threshold_days
        )
        return True
    return False


async def trigger_escape_hatch_export(
    conn: aiosqlite.Connection, export_dir: str | Path
) -> dict[str, Any]:
    """Dumps all SQLite tables to open formats (.jsonl) in the target directory."""
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    # Get all tables
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in await cursor.fetchall()]

    exported_files = {}
    schema_manifest = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    for table in tables:
        # Fetch columns/schema info
        col_cursor = await conn.execute(f"PRAGMA table_info({table});")
        columns_info = await col_cursor.fetchall()
        columns = [col[1] for col in columns_info]
        column_types = {col[1]: col[2] for col in columns_info}

        schema_manifest["tables"][table] = {
            "columns": columns,
            "types": column_types,
            "filename": f"{table}.jsonl",
        }

        # Query rows
        row_cursor = await conn.execute(f"SELECT * FROM {table};")
        rows = list(await row_cursor.fetchall())

        table_file = export_path / f"{table}.jsonl"
        with open(table_file, "w", encoding="utf-8") as f:
            for row in rows:
                row_dict = dict(zip(columns, row, strict=True))
                f.write(json.dumps(row_dict, sort_keys=True) + "\n")

        exported_files[table] = str(table_file)
        logger.info("Exported table %s → %s (%d rows)", table, table_file, len(rows))

    manifest_file = export_path / "schema.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(schema_manifest, f, indent=2, sort_keys=True)

    return {
        "status": "success",
        "export_dir": str(export_path),
        "exported_files": exported_files,
        "manifest_path": str(manifest_file),
    }
