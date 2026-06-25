#!/usr/bin/env python3
"""
cortex/nodes/goat_math_stress.py
═══════════════════════════════════════════════════════════════
GOAT-MATH: Prueba de Estrés Termodinámico (C5-REAL)
═══════════════════════════════════════════════════════════════
Objetivo: Validar Regla R10 (Concurrencia Confiable de DB).
Prueba inyección y mutación concurrente masiva usando WAL mode.
"""

import concurrent.futures
import random
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
import time
from pathlib import Path

from babylon60.database.core import connect as db_connect

DB_PATH = Path("babylon60.db")

def worker_task(worker_id: int, iterations: int):
    """Simula validaciones concurrentes agresivas."""
    # R10: Factor de conexión rígido con busy_timeout de 5000ms
    conn = db_connect(str(DB_PATH), timeout=5)
    
    successes = 0
    failures = 0
    
    for _ in range(iterations):
        node_idx = random.randint(1, 100)
        node_id = f"GOAT-MATH-{node_idx:03d}"
        
        try:
            # Lectura agresiva
            cursor = conn.execute(
                "SELECT validation_status FROM goat_math_nodes WHERE id = ?",
                (node_id,)
            )
            cursor.fetchone()
            
            # Escritura agresiva
            new_status = 'VALIDATED' if random.random() > 0.5 else 'PENDING'
            conn.execute(
                "UPDATE goat_math_nodes SET validation_status = ? WHERE id = ?",
                (new_status, node_id)
            )
            conn.commit()
            successes += 1
        except sqlite3.OperationalError:
            failures += 1
            # Backoff forzado en caso de busy
            time.sleep(0.01)
            
    conn.close()
    return worker_id, successes, failures

def run_stress_test(num_workers: int = 50, iterations_per_worker: int = 200):
    print("=" * 70)
    print("🐐 INICIANDO PRUEBA DE ESTRÉS (R10: CONCURRENCIA SQLite WAL)")
    print("=" * 70)
    print(f"Workers: {num_workers} | Iteraciones/worker: {iterations_per_worker}")
    print(f"Total transacciones esperadas: {num_workers * iterations_per_worker}")
    
    start_time = time.time()
    
    total_success = 0
    total_fail = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_task, i, iterations_per_worker) for i in range(num_workers)]
        
        for future in concurrent.futures.as_completed(futures):
            wid, suc, fail = future.result()
            total_success += suc
            total_fail += fail

    duration = time.time() - start_time
    
    print("-" * 70)
    print(f"⏱️  Tiempo total: {duration:.2f}s")
    print(f"✅ Transacciones Exitosas: {total_success}")
    print(f"❌ Transacciones Fallidas (Deadlocks): {total_fail}")
    print(f"⚡ Throughput: {(total_success+total_fail)/duration:.2f} tx/s")
    
    if total_fail == 0:
        print("\n✅ ESTADO TERMODINÁMICO: ESTABLE. REGLA R10 SUPERADA.")
    else:
        print("\n❌ ALARMA: ENTROPÍA DETECTADA. DEADLOCKS PRESENTES.")
        
    print("=" * 70)

if __name__ == "__main__":
    run_stress_test()
