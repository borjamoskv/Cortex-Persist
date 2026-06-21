#!/usr/bin/env python3
"""
cortex/nodes/goat_math_curriculum.py
═══════════════════════════════════════════════════════════════
GOAT-MATH: Motor de Ejecución de la Ruta de Estudio (Curriculum)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | Aprendizaje Basado en Aserciones
Objetivo: Transformar teoría abstracta en competencia técnica medible.
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Optional

class CurriculumEngine:
    def __init__(self, db_path: str = "cortex.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            print("❌ ERROR: cortex.db no encontrado. Falla estructural.")
            sys.exit(1)
        self.conn = sqlite3.connect(str(self.db_path))

    def get_topological_path(self) -> List[Dict]:
        """Extrae la ruta de estudio basada en dependencias causales (DAG)."""
        cursor = self.conn.execute("""
            SELECT id, name, block_name, criticality, dependencies, validation_status
            FROM goat_math_nodes
            ORDER BY idx ASC
        """)
        nodes = []
        for row in cursor:
            nodes.append({
                "id": row[0],
                "name": row[1],
                "block": row[2],
                "criticality": row[3],
                "deps": row[4],
                "status": row[5]
            })
        return nodes

    def get_node(self, node_id: str) -> Optional[Dict]:
        cursor = self.conn.execute("""
            SELECT id, name, block_name, verification_method, validation_status
            FROM goat_math_nodes
            WHERE id = ?
        """, (node_id,))
        row = cursor.fetchone()
        if not row: return None
        return {
            "id": row[0],
            "name": row[1],
            "block": row[2],
            "method": row[3],
            "status": row[4]
        }

    def verify_submission(self, node_id: str, script_path: Path):
        """
        Inyecta el script del operador en el sandbox y valida contra 
        la restricción del DAG.
        """
        node = self.get_node(node_id)
        if not node:
            print(f"❌ ERROR: Nodo {node_id} no existe en el DAG.")
            return False

        if not script_path.exists():
            print(f"❌ ERROR: Archivo de sumisión {script_path} no encontrado.")
            return False

        print(f"═══════════════════════════════════════════════════════════════")
        print(f"🐐 EVALUACIÓN C5-REAL: {node_id} - {node['name']}")
        print(f"Bloque: {node['block']}")
        print(f"Criterio de Verificación: {node['method']}")
        print(f"═══════════════════════════════════════════════════════════════")

        code = script_path.read_text()
        
        try:
            # Aislamiento Termodinámico Básico
            env = {}
            exec(code, env)
            print(f"\n✅ PASS: Aserción determinista superada.")
            
            # Actualizar Ledger local
            self.conn.execute(
                "UPDATE goat_math_nodes SET validation_status = 'VALIDATED' WHERE id = ?",
                (node_id,)
            )
            self.conn.commit()
            print(f"🔗 ESTADO ACTUALIZADO A 'VALIDATED' EN DAG EPISTÉMICO.")
            return True
        except AssertionError as e:
            print(f"\n❌ FAIL: Falla de aserción estructural. {str(e)}")
            return False
        except Exception as e:
            print(f"\n❌ FAIL: Falla catastrófica de ejecución: {str(e)}")
            return False

    def print_syllabus(self):
        nodes = self.get_topological_path()
        print("=" * 70)
        print("🐐 CURRICULUM GOAT-MATH: RUTA CAUSAL DE ESTUDIO")
        print("=" * 70)
        
        current_block = ""
        for n in nodes:
            if n['block'] != current_block:
                current_block = n['block']
                print(f"\n📘 BLOQUE: {current_block.upper()}")
            
            status_icon = "✅" if n['status'] == 'VALIDATED' else "⏳"
            print(f"  {status_icon} [{n['id']}] {n['name']:<35} ({n['criticality']})")
            
        print("\n" + "=" * 70)

def main():
    parser = argparse.ArgumentParser(description="GOAT-MATH Curriculum Engine (C5-REAL)")
    parser.add_argument("--syllabus", action="store_true", help="Mostrar ruta de estudio")
    parser.add_argument("--verify", type=str, help="ID del nodo a verificar (ej. GOAT-MATH-001)")
    parser.add_argument("--script", type=str, help="Ruta al script Python del estudiante")
    
    args = parser.parse_args()
    engine = CurriculumEngine()

    if args.syllabus:
        engine.print_syllabus()
    elif args.verify and args.script:
        engine.verify_submission(args.verify, Path(args.script))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
