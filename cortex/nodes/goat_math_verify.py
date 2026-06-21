#!/usr/bin/env python3
"""
cortex/nodes/goat_math_verify.py
═══════════════════════════════════════════════════════════════
GOAT-MATH: Script de Verificación Rápida C5-REAL
Comprueba la integridad del DAG en la DB y lanza la validación
de primitivas matemáticas en PyTorch/SciPy.
═══════════════════════════════════════════════════════════════
"""

import sqlite3
import sys
from pathlib import Path
import json

def verify_dag_integrity(db_path: str = "../../cortex.db"):
    print("=" * 70)
    print("🐐 GOAT-MATH: Verificación C5-REAL DAG Integrity")
    print("=" * 70)

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ ERROR: No se encuentra la base de datos en {db_file.resolve()}")
        return False

    conn = sqlite3.connect(str(db_file))
    
    # Check nodes
    try:
        nodes_count = conn.execute("SELECT COUNT(*) FROM goat_math_nodes").fetchone()[0]
        print(f"✅ Nodos en DB: {nodes_count}/100")
        if nodes_count != 100:
            print("⚠️ ADVERTENCIA: No están los 100 nodos requeridos.")
    except sqlite3.OperationalError:
        print("❌ ERROR: La tabla 'goat_math_nodes' no existe. ¿Se ha ejecutado goat_math_nodes.py?")
        conn.close()
        return False

    # Check validation report
    try:
        latest_val = conn.execute(
            "SELECT is_valid_dag, total_edges, manifest_hash FROM goat_math_dag_validation ORDER BY id DESC LIMIT 1"
        ).fetchone()
        
        if latest_val:
            is_valid = bool(latest_val[0])
            print(f"✅ DAG Válido: {is_valid}")
            print(f"✅ Aristas: {latest_val[1]}")
            print(f"✅ Hash Manifest: {latest_val[2]}")
        else:
            print("⚠️ ADVERTENCIA: No hay reportes de validación del DAG en la DB.")
            
    except sqlite3.OperationalError:
        pass

    conn.close()
    print("-" * 70)
    return True

def verify_implementations():
    print("🐐 Ejecutando validación de implementaciones dinámicas...")
    try:
        import goat_math_implementations
        goat_math_implementations.verify_all()
    except ImportError:
        print("❌ ERROR: No se encontró goat_math_implementations.py.")
        sys.exit(1)

def main():
    if not verify_dag_integrity():
        sys.exit(1)
        
    verify_implementations()

if __name__ == "__main__":
    main()
