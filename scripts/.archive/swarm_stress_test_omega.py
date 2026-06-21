# [C5-REAL] Exergy-Maximized
import asyncio
import logging
import random
import sys
import time

# Configuración de logging denso
setup_cortex_logging()

# === PARÁMETROS DEL ENJAMBRE ===
TARGET_COUNT = 10000
CONCURRENCY_LIMIT = 100
FAILURE_RATE = 0.20  # 20% de fallos aleatorios


class ChaosMonkeyEngine:
    """
    Simula ingesta con asfixia térmica, latencia caótica y fallos de red duros.
    """

    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.duplicate_guard = set()
        self.lock = asyncio.Lock()

    async def simulate_ingest(self, target_id: str):
        # 1. Chequeo de duplicidad estricta (Idempotencia)
        async with self.lock:
            if target_id in self.duplicate_guard:
                logging.error(f"¡DUPLICADO DETECTADO! Fallo crítico de arquitectura: {target_id}")
                raise RuntimeError(f"Duplicate work: {target_id}")
            self.duplicate_guard.add(target_id)

        # 2. Latencia caótica (0.01s a 0.1s)
        await asyncio.sleep(random.uniform(0.01, 0.1))

        # 3. Inyección de fallos (20%)
        if random.random() < FAILURE_RATE:
            async with self.lock:
                self.failure_count += 1
                self.duplicate_guard.remove(target_id)  # Permite reintento al fallar
            raise ConnectionError(f"Chaos Monkey 💥: Red denegada en {target_id}")

        async with self.lock:
            self.success_count += 1
        return f"{target_id}_PROCESSED"


async def worker(worker_id: int, queue: asyncio.Queue, engine: ChaosMonkeyEngine, stats: dict):
    while True:
        try:
            target_id = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        try:
            # Intentar procesar con lógica de reintentos
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                try:
                    await engine.simulate_ingest(target_id)
                    stats["completed"] += 1
                    break
                except ConnectionError:
                    if attempt == max_retries:
                        stats["failed_final"] += 1
                        logging.warning(f"Target {target_id} abortado tras {max_retries} intentos.")
                    else:
                        # Exponential backoff con Jitter
                        delay = (0.05 * (2**attempt)) + random.uniform(0, 0.05)
                        await asyncio.sleep(delay)
        finally:
            queue.task_done()


async def execute_swarm():
    logging.info(
        f"Iniciando Chaos Swarm: {TARGET_COUNT} targets | {CONCURRENCY_LIMIT} workers | {FAILURE_RATE * 100}% Error Rate"
    )

    engine = ChaosMonkeyEngine()
    queue = asyncio.Queue()
    stats = {"completed": 0, "failed_final": 0}

    # Cargar targets
    for i in range(TARGET_COUNT):
        queue.put_nowait(f"TARGET_{i:05d}")

    start_time = time.time()

    # Desplegar enjambre
    workers = []
    for i in range(CONCURRENCY_LIMIT):
        workers.append(asyncio.create_task(worker(i, queue, engine, stats)))

    # Monitor de latido asíncrono
    async def monitor():
        while not queue.empty():
            await asyncio.sleep(2)
            logging.info(
                f"Progreso: {stats['completed']}/{TARGET_COUNT} | Queue: {queue.qsize()} | Retry Drops: {stats['failed_final']}"
            )

    monitor_task = asyncio.create_task(monitor())

    await asyncio.gather(*workers)
    monitor_task.cancel()

    elapsed = time.time() - start_time
    throughput = TARGET_COUNT / elapsed

    sys.stdout.write("\n" + "=" * 50 + "\n")
    sys.stdout.write("REPORTE DE ESTRÉS (VECTOR A)\n")
    sys.stdout.write("=" * 50 + "\n")
    sys.stdout.write(f"Targets Procesados: {stats['completed']}\n")
    sys.stdout.write("Tasa de Duplicados: 0 (Garantizado por Mutex)\n")
    sys.stdout.write(f"Abortos (Finales):  {stats['failed_final']}\n")
    sys.stdout.write(f"Throughput:         {throughput:.2f} ops/sec\n")
    sys.stdout.write(f"Tiempo Total:       {elapsed:.2f} s\n")
    sys.stdout.write(f"Fallos Inyectados:  {engine.failure_count} (Manejados por Jitter/Backoff)\n")
    sys.stdout.write("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(execute_swarm())
