#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
CRONOS 1H Harness - 50-Cycle MEJORAlo Loop Orchestrator

Forces strict bounds on autonomous optimization:
- Max 50 iterations.
- Max 3600 seconds (1 Hour).
- Prevents infinite Agent Ecosystem recursion.
"""

import os
import subprocess
import time
import sys

MAX_CYCLES = 50
MAX_TIME_SECONDS = 3600
PROJECT_NAME = "cortex-persist"
TARGET_DIR = "."

def run_cronos_loop():
    start_time = time.monotonic()
    
    print(f"🚀 Iniciando CRONOS 1H (Max {MAX_CYCLES} ciclos, Max {MAX_TIME_SECONDS}s)")
    
    for cycle in range(1, MAX_CYCLES + 1):
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_TIME_SECONDS:
            print(f"🛑 CRONOS ABORT: Tiempo máximo excedido ({elapsed:.1f}s).")
            sys.exit(0)
            
        print(f"\n" + "="*50)
        print(f"🔄 CICLO MEJORA {cycle}/{MAX_CYCLES} [Elapsed: {elapsed:.1f}s]")
        print("="*50)
        
        # Ejecutamos el scanner con auto-curación y profundidad total
        cmd = [
            "python3", "-m", "cortex.cli", "mejoralo", "scan", 
            PROJECT_NAME, TARGET_DIR, "--deep", "--auto-heal"
        ]
        
        try:
            result = subprocess.run(cmd, check=False)
            
            if result.returncode == 0:
                print(f"✅ Ciclo {cycle} completado con éxito.")
            else:
                print(f"⚠️ Ciclo {cycle} finalizado con advertencias (exit code: {result.returncode}).")
                
            # Parseamos el score actual o verificamos el ghost
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR en ciclo {cycle}: {e}")
            break
            
    total_time = time.monotonic() - start_time
    print(f"🏁 CRONOS FINALIZADO: {MAX_CYCLES} completados en {total_time:.1f}s.")

if __name__ == "__main__":
    run_cronos_loop()
