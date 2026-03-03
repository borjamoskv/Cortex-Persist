"""
CORTEX Global Casing Purge (Ω₁: Canonical Mapping).

Unifies fragmented project names across all materialized views in the Ledger.
Excludes the immutable 'transactions' table to respect Ledger integrity.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

# Configuración del Logger Soberano
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cortex.global_purge")

DB_PATH = Path.home() / ".cortex" / "cortex.db"

# Mapeo de Unificación Global (Ω₁: Canonical Mapping)
# Colapsamos variantes de casing y sub-nombres en versiones UPPERCASE canónicas.
NAMESPACE_MAP = {
    # ── CORTEX core ───────────────────────────────────────────
    "cortex": "CORTEX",
    "Cortex": "CORTEX",
    "cortex-v7": "CORTEX",
    "CORTEX_V7": "CORTEX",
    "CORTEX_V8": "CORTEX",
    "CORTEX-Core": "CORTEX",
    "CORTEX-Daemon": "CORTEX",
    "cortex-persist": "CORTEX-PERSIST",
    "Cortex-Persist": "CORTEX-PERSIST",
    "cortexpersist": "CORTEX-PERSIST",
    "cortex-landing": "CORTEX-LANDING",
    "landing": "CORTEX-LANDING",
    # ── Proyectos Experimentales ────────────────────────────────
    "moltbook": "MOLTBOOK",
    "Moltbook": "MOLTBOOK",
    "moskv-1": "MOSKV-1",
    "moskv": "MOSKV-1",
    "moskv-swarm": "MOSKV-SWARM",
    "naroa": "NAROA",
    "naroa-2026": "NAROA",
    "naroa-web": "NAROA",
    "NAROA_2026": "NAROA",
    "livenotch": "LIVENOTCH",
    "live-notch": "LIVENOTCH",
    "live-notch-swift": "LIVENOTCH",
    "notch-live": "LIVENOTCH",
    "mailtv-1": "MAILTV-1",
    "mailing": "MAILTV-1",
    "moneytv": "MONEYTV-1",
    "moneytv-1": "MONEYTV-1",
    "antigravity": "ANTIGRAVITY",
    "autorouter": "AUTOROUTER-1",
    "autorouter-1": "AUTOROUTER-1",
    "omega-singularity": "OMEGA-SINGULARITY",
    "ouroboros": "OUROBOROS",
    "Ouroboros": "OUROBOROS",
}


def global_casing_purge() -> None:
    """Executes the global namespace unifications."""
    if not DB_PATH.exists():
        logger.error("Base de datos no encontrada en %s", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    tables_to_update = [
        "facts",
        "heartbeats",
        "time_entries",
        "entities",
        "episodes",
        "causal_edges",
    ]

    modified_rows = 0

    try:
        logger.info("🚀 Iniciando GLOBAL CASING PURGE (Mapping %d pairs)", len(NAMESPACE_MAP))

        for table in tables_to_update:
            # Verificar si la tabla existe
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)
            )
            if not cursor.fetchone():
                continue

            for source, target in NAMESPACE_MAP.items():
                if source == target:
                    continue

                cursor.execute(
                    f"UPDATE {table} SET project = ? WHERE project = ?", (target, source)
                )
                rows = cursor.rowcount
                if rows > 0:
                    logger.info(
                        "  ✅ %s: %d filas migradas (%s -> %s)", table, rows, source, target
                    )
                    modified_rows += rows

        # Especial: facts_fts (actualizar la columna project)
        try:
            for source, target in NAMESPACE_MAP.items():
                if source == target:
                    continue
                cursor.execute(
                    "UPDATE facts_fts SET project = ? WHERE project = ?", (target, source)
                )
        except sqlite3.Error:
            pass

        conn.commit()
        logger.info("✨ Purga global completada. %d filas afectadas.", modified_rows)

    except sqlite3.Error as e:
        conn.rollback()
        logger.error("❌ Error durante la purga: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    global_casing_purge()
