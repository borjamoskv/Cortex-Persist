#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
ENTROPY-0: El Guardián de la Deuda Técnica.
Este hook de pre-commit aborta el commit si la puntuación de MEJORAlo cae por debajo de 90.
"""

import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import subprocess
import sys
from pathlib import Path

__all__ = ["main"]


def main():
    print("🛡️  ENTROPY-0: Validando entropía del código...")

    # Comprobar si hay archivos Python modificados en staging
    try:
        staged_files = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], text=True
        ).splitlines()
    except subprocess.CalledProcessError:
        print("❌ Error al obtener archivos cacheados.")
        sys.exit(1)

    python_files = [f for f in staged_files if f.endswith(".py")]

    if not python_files:
        print("⏭️  No hay archivos Python en staging. Omitiendo X-Ray 13D.")
        sys.exit(0)

    # Solo necesitamos el nombre del proyecto, que suele ser el nombre del directorio actual
    project_name = Path.cwd().name

    # Ejecutar cortex mejoralo scan
    print(f"🔍 Ejecutando X-Ray 13D en '{project_name}'...")
    try:
        from legacy_research.mejoralo import MejoraloEngine

        from cortex.cli import DEFAULT_DB, get_engine

        engine = get_engine(DEFAULT_DB)
        m = MejoraloEngine(engine)

        # Ocultar temporalmente el stdout normal para no saturar, o dejarlo si falla.
        # Mejoralo.scan devuelve un ScoreTracker u objeto con .score
        # Escaneamos el directorio raíz completo para asegurar integridad.
        result = m.scan(project_name, str(Path.cwd()), deep=False)
        import asyncio

        asyncio.run(engine.close())

    except ImportError:
        print("⚠️  Advertencia: Cortex no está disponible en este entorno. Omitiendo.")
        sys.exit(0)
    except (RuntimeError, ValueError, sqlite3.Error) as e:
        print(f"❌ Error al ejecutar MEJORAlo: {e}")
        sys.exit(1)

    score = result.score

    if score < 90:
        print("\n" + "=" * 50)
        print("🚨 ALERTA DE ENTROPÍA: COMMIT RECHAZADO 🚨")
        print("=" * 50)
        print("La regla soberana ENTROPY-0 exige una puntuación MEJORAlo >= 90.")
        print(f"Puntuación actual: {score}/100")
        print("La mediocridad es crimen. Por favor, usa:")
        print("  cortex mejoralo scan <proyecto> .")
        print("  cortex mejoralo --brutal (si es necesario)")
        print("=" * 50 + "\n")
        sys.exit(1)

    print(f"✅ Entropía controlada (Score: {score}). Commit permitido.")
    sys.exit(0)


if __name__ == "__main__":
    main()
