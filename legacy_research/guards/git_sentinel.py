#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Git Sentinel (Path 5).
Intercepts git commits at the commit-msg stage.
Rejects messages that are vague, low-entropy, or contain Green Theater.
Enforces thermodynamic rigor on the human operator.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from cortex.guards.exergy_guard import calculate_exergy
except ImportError:
    print("\n[C5-REAL] ERROR FATAL: No se puede importar calculate_exergy. Abortando commit.")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("[C5-REAL] ERROR: No commit message file provided.")
        sys.exit(1)
        
    commit_msg_file = sys.argv[1]
    
    with open(commit_msg_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Strip git comments and empty lines
    msg_lines = [line.strip() for line in lines if not line.strip().startswith("#")]
    raw_msg = " ".join(msg_lines).strip()
    
    if not raw_msg:
        sys.exit(0) # Let commitlint handle empty messages

    # C5-REAL Anti-patterns
    low_exergy_words = [
        "fix error", "update", "changes", "wip", "stuff", "test", 
        "fixed bug", "minor change", "refactor"
    ]
    
    msg_lower = raw_msg.lower()
    
    # 1. Brutal Strictness for vague messages
    if raw_msg in low_exergy_words or len(raw_msg.split()) < 3:
        print(f"\n[C5-REAL] 🛑 RECHAZO TERMODINÁMICO.")
        print(f"El mensaje de commit '{raw_msg}' carece de exergía causal.")
        print("Axioma L2: La memoria es frágil, el estado es sagrado. Describe QUÉ y POR QUÉ mutó el estado.")
        sys.exit(1)
        
    # 3. Shannon Entropy / Exergy Check
    exergy_score = calculate_exergy(raw_msg)
    
    # Minimum exergy for a commit message is 0.35
    if exergy_score < 0.35:
        print(f"\n[C5-REAL] 🛑 RECHAZO POR ANERGÍA (Score: {exergy_score:.2f} < 0.35).")
        print("El mensaje contiene ruido estadístico o es demasiado vago para cristalizar el estado del Grafo.")
        print("Reescribe utilizando el Lexicón Exérgico (ej. 'feat(core): inyectar interceptor BFT en ATMS').")
        sys.exit(1)
        
    # Success
    print(f"\n[C5-REAL] Commit autorizado. Exergía: {exergy_score:.2f}")
    sys.exit(0)

if __name__ == "__main__":
    main()
