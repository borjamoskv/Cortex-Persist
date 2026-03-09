import logging
import sqlite3
from pathlib import Path

# Configuración del Logger Soberano
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cortex.namespace_collapse")

DB_PATH = Path.home() / ".cortex" / "cortex.db"
CANONICAL_PROJECT = "CORTEX"
TARGET_PROJECTS = ["cortex", "Cortex"]


def collapse_namespaces():
    if not DB_PATH.exists():
        logger.error("Base de datos no encontrada en %s", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Tablas a actualizar (materializadas, no el ledger inmutable)
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
        logger.info("🚀 Iniciando colapso de namespaces %s -> %s", TARGET_PROJECTS, CANONICAL_PROJECT)

        for table in tables_to_update:
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                logger.warning("  ⚠️ Tabla '%s' no existe, omitiendo.", table)
                continue

            for target in TARGET_PROJECTS:
                cursor.execute(
                    f"UPDATE {table} SET project = ? WHERE project = ?", (CANONICAL_PROJECT, target)
                )
                rows = cursor.rowcount
                if rows > 0:
                    logger.info(
                        "  ✅ %s: %s filas migradas (%s -> %s)", table, rows, target, CANONICAL_PROJECT
                    )
                    modified_rows += rows

        # FTS Tables (son un poco especiales, a veces tienen sus propias tablas de contenido)
        # En FTS5, si se usó content='table', hay que refrescar.
        # Si no, se actualizan como tablas normales si el esquema lo permite.
        fts_tables = ["facts_fts", "episodes_fts"]
        for fts_table in fts_tables:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (fts_table,)
            )
            if cursor.fetchone():
                for target in TARGET_PROJECTS:
                    # En FTS5, esto a veces requiere un 'delete' y luego 'insert' o 'rebuild'
                    # pero si solo actualizamos el proyecto en la tabla de contenido,
                    # el índice FTS podría quedar desincronizado hasta el próximo REBUILD.
                    # Intentaremos el UPDATE directo primero.
                    try:
                        cursor.execute(
                            f"UPDATE {fts_table} SET project = ? WHERE project = ?",
                            (CANONICAL_PROJECT, target),
                        )
                    except sqlite3.Error:
                        logger.warning(
                            "  ⚠️ No se pudo actualizar %s directamente (esperado en FTS).", fts_table
                        )

        conn.commit()
        logger.info("✨ Colapso completado. %s filas afectadas.", modified_rows)

    except sqlite3.Error as e:
        conn.rollback()
        logger.error("❌ Error durante la migración: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    collapse_namespaces()
