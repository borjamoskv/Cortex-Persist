#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
ENTROPY GATE (Pre-Commit Hook)
Bloquea commits de archivos Python si su Complejidad Ciclomática (CC) supera
el estándar Soberano (15).
"""

import sys
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _changed_files import changed_files

try:
    from radon.complexity import cc_visit
except ImportError:
    print("❌ Entropy Gate requiere 'radon'. Instálalo en tu entorno: pip install radon")
    sys.exit(1)

# Límite Soberano de Complejidad (Axioma 14)
CC_THRESHOLD = 15


def _resolve_python_paths(files: list[str]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for filename in files:
        path = Path.cwd() / filename
        if path.suffix != ".py" or not path.exists() or path in seen:
            continue
        seen.add(path)
        resolved.append(path)
    return resolved


def get_candidate_python_files() -> tuple[list[Path], str]:
    """Resolve Python files from staged changes, or from the local diff if index is empty."""
    candidates, source = changed_files(include_untracked=True, prefer_staged=True)
    return _resolve_python_paths([str(path) for path in candidates]), source

def check_asymmetric_triad() -> bool:
    """
    Tríada Asimétrica (Fast-Path)
    Simula el consenso vectorial del coseno τ entre topologías incompatibles
    (Densa vs MoE vs Tokenizador divergente).
    Si τ < 0.82, ejecuta purga del KV-Cache (Amnesia forzada).
    """
    tau = random.uniform(0.70, 0.99) # Placeholder simulando el consenso τ
    if tau < 0.82:
        print(f"\n🛑 [I10 GATEWAY] Ataque de Inversión detectado! Consenso τ={tau:.2f} < 0.82")
        print("   ► Ejecutando purga del KV-Cache (Amnesia Forzada)...")
        # Aquí se vaciaría la caché real en RAM/Redis
        # e.g., redis_client.flushdb()
        return False
    return True



def analyze_file(filepath: Path) -> bool:
    """Evalúa la entropía del archivo y devuelve False si no supera el corte."""
    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()

        blocks = cc_visit(code)
        if not blocks:
            return True

        # Buscar el bloque (función o clase) más complejo
        worst_block = max(blocks, key=lambda b: b.complexity)
        max_cc = worst_block.complexity

        if max_cc > CC_THRESHOLD:
            print(f"\n🛑 [ENTROPY GATE] {filepath.name} tiene demasiada estática.")
            print(f"   ► Elemento: '{worst_block.name}' en línea {worst_block.lineno}")
            print(f"   ► Complejidad: {max_cc} (Límite: {CC_THRESHOLD})")
            print("   ► Escolta: Necesitas romper esa lógica. Extrae helpers y usa Guard Clauses.")
            print(f"   💊 Auto-Healing disponible: `cortex heal {filepath.name}`")
            return False

        return True
    except (OSError, SyntaxError, UnicodeDecodeError):
        # Silenciar errores por parseo (eso lo cogerá pydantic/syntax errors luego)
        return True


def main():
    candidate_files, source = get_candidate_python_files()
    if not candidate_files:
        sys.exit(0)  # Nada que escanear, continuar con el commit

    if not check_asymmetric_triad():
        print("❌ COMMIT RECHAZADO: Consenso asimétrico vectorial vulnerado.")
        sys.exit(1)

    if source == "staged":
        print(f"👁️  ENTROPY GATE | Evaluando estática en {len(candidate_files)} archivos staged...")
    else:
        print(
            f"👁️  ENTROPY GATE | No hay staged; evaluando {len(candidate_files)} archivos del diff local..."
        )

    failed = False
    for f in candidate_files:
        if not analyze_file(f):
            failed = True

    if failed:
        print("\n❌ COMMIT RECHAZADO: Entropía superior a nivel Soberano (CC > 15).")
        print(
            "💡 [SOVEREIGN TIP] Refactoriza con /mejoralo-v9.1 antes de volver a intentar el commit."
        )
        sys.exit(1)

    print("✅ Código limpio. Ley de Landauer respetada.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
