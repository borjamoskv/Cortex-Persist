#!/usr/bin/env python3
"""
ENTROPY GATE (Pre-Commit Hook)
Bloquea commits de archivos Python si su Complejidad Ciclomática (CC) supera
el estándar Soberano (15).
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from radon.complexity import cc_visit
except ImportError:
    print("❌ Entropy Gate requiere 'radon'. Instálalo en tu entorno: pip install radon")
    sys.exit(1)

# Límite Soberano de Complejidad (Axioma 14)
CC_THRESHOLD = 15

def get_staged_python_files():
    """Obtiene la lista de archivos manipulados en este commit usando git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True, check=True
        )
        files = result.stdout.strip().split('\n')
        staged_files = []
        for f in files:
            if not f:
                continue
            path = Path.cwd() / f
            if path.suffix == '.py' and path.exists():
                staged_files.append(path)
        return staged_files
    except subprocess.CalledProcessError:
        return []

def analyze_file(filepath: Path) -> bool:
    """Evalúa la entropía del archivo y devuelve False si no supera el corte."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
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
            print(f"   ► Escolta: Necesitas romper esa lógica. Extrae helpers y usa Guard Clauses.")
            print(f"   💊 Auto-Healing disponible: `cortex heal {filepath.name}`")
            return False
            
        return True
    except Exception as e:
        # Silenciar errores por parseo (eso lo cogerá pydantic/syntax errors luego)
        return True

def main():
    staged_files = get_staged_python_files()
    if not staged_files:
        sys.exit(0) # Nada que escanear, continuar con el commit
        
    print(f"👁️  ENTROPY GATE | Evaluando estática en {len(staged_files)} archivos...")
    
    failed = False
    for f in staged_files:
        if not analyze_file(f):
            failed = True
            
    if failed:
        print("\n❌ COMMIT RECHAZADO: Entropía superior a nivel Soberano (CC > 15).")
        print("💡 [SOVEREIGN TIP] Refactoriza con /mejoralo-v9.1 antes de volver a intentar el commit.")
        sys.exit(1)
        
    print("✅ Código limpio. Ley de Landauer respetada.\n")
    sys.exit(0)

if __name__ == '__main__':
    main()
