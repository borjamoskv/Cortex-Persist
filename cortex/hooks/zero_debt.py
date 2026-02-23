#!/usr/bin/env python3
"""
ENTROPY-0: El Guardián de la Deuda Técnica.
Este hook de pre-commit aborta el commit si la puntuación de MEJORAlo cae por debajo de 90.
"""

import sqlite3
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
        from cortex.cli import DEFAULT_DB, get_engine
        from cortex.mejoralo import MejoraloEngine

        engine = get_engine(DEFAULT_DB)
        m = MejoraloEngine(engine)

        # Ocultar temporalmente el stdout normal para no saturar, o dejarlo si falla.
        # Mejoralo.scan devuelve un ScoreTracker u objeto con .score
        # Escaneamos el directorio raíz completo para asegurar integridad.
        result = m.scan(project_name, str(Path.cwd()), deep=False)
        engine.close_sync()

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
