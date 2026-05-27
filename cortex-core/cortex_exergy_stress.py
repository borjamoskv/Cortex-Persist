import asyncio
import time
import threading
import os
from persistence import HybridPersistenceManager, enqueue_swarm_task
import sqlite3

async def run_stress_test():
    print("[+] Inicializando HybridPersistenceManager (Outbox Daemon)...")
    HybridPersistenceManager()
    
    # Red externa eliminada, operamos en aislamiento Ring-0
    
    # Preparar Ring Buffer limpio para la prueba
    from persistence import _get_ring_buffer
    _get_ring_buffer().reset()

    NUM_TASKS = 10000
    print(f"[+] Inyectando {NUM_TASKS} tareas en ráfaga (Simulación de Enjambre Masivo)...")
    
    start_time = time.monotonic()
    for i in range(NUM_TASKS):
        # Fire-and-forget payload
        enqueue_swarm_task("OPTIMIZER", {"task_id": i, "vector": "exergy_max"})
    
    enqueue_duration = time.monotonic() - start_time
    print(f"[+] {NUM_TASKS} tareas encoladas en {enqueue_duration:.4f} segundos.")
    print(f"[+] Velocidad de ingestión (I/O Exergía): {NUM_TASKS/enqueue_duration:.2f} tareas/segundo.")
    
    # Medir overhead de sistema operativo (Hilos vivos)
    active_threads = threading.active_count()
    print(f"[+] Hilos del Sistema Operativo Activos: {active_threads} (Esperado: < 5, Demuestra aniquilación de fricción)")
    
    # Esperar unos segundos para ver al Outbox Daemon drenando
    print("[+] Observando drenaje del Outbox Daemon durante 3 segundos...")
    await asyncio.sleep(3.0)
    
    from persistence import _get_ring_buffer
    ring = _get_ring_buffer()
    pending = ring.get_pending_count()
    
    print("[+] Estado final de la cola (L4 Ring Buffer):")
    print(f"    - PENDING: {pending}")
    print(f"    - PROCESSED/DROPPED: {NUM_TASKS - pending}")
    
    print("[!] STRESS TEST C5-REAL COMPLETADO.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
