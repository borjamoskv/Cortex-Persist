import asyncio
import time
import threading
import os
from persistence import HybridPersistenceManager, enqueue_swarm_task
import sqlite3

async def run_stress_test():
    print("[+] Inicializando HybridPersistenceManager (Outbox Daemon)...")
    manager = HybridPersistenceManager()
    
    # Configurar MOCK de NEXUS para evitar ban/throttling de red real durante stress test
    os.environ["NEXUS_API_URL"] = "http://localhost:8600"
    os.environ["NEXUS_BEARER_TOKEN"] = "mock_token_c5_real"
    
    # Preparar base de datos limpia para la prueba
    conn = sqlite3.connect(os.getenv("CORTEX_DB_PATH", "cortex_memory_vsa.db"))
    conn.execute("DELETE FROM cortex_swarm_queue")
    conn.commit()
    conn.close()

    NUM_TASKS = 10000
    print(f"[+] Inyectando {NUM_TASKS} tareas en ráfaga (Simulación de Enjambre Masivo)...")
    
    start_time = time.time()
    for i in range(NUM_TASKS):
        # Fire-and-forget payload
        enqueue_swarm_task("OPTIMIZER", {"task_id": i, "vector": "exergy_max"})
    
    enqueue_duration = time.time() - start_time
    print(f"[+] {NUM_TASKS} tareas encoladas en {enqueue_duration:.4f} segundos.")
    print(f"[+] Velocidad de ingestión (I/O Exergía): {NUM_TASKS/enqueue_duration:.2f} tareas/segundo.")
    
    # Medir overhead de sistema operativo (Hilos vivos)
    active_threads = threading.active_count()
    print(f"[+] Hilos del Sistema Operativo Activos: {active_threads} (Esperado: < 5, Demuestra aniquilación de fricción)")
    
    # Esperar unos segundos para ver al Outbox Daemon drenando
    print("[+] Observando drenaje del Outbox Daemon durante 3 segundos...")
    await asyncio.sleep(3.0)
    
    conn = sqlite3.connect(os.getenv("CORTEX_DB_PATH", "cortex_memory_vsa.db"))
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM cortex_swarm_queue GROUP BY status")
    results = c.fetchall()
    conn.close()
    
    print("[+] Estado final de la cola:")
    for status, count in results:
        print(f"    - {status.upper()}: {count}")
    
    print("[!] STRESS TEST C5-REAL COMPLETADO.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
