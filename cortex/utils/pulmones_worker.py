import asyncio
import sqlite3
import json
import time
import logging
from pathlib import Path
from importlib import import_module

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CORTEX.PULMONES.WORKER")

class PulmonesWorker:
    """Daemon soberano que drena la cola de fallos SQLite de forma asíncrona."""
    
    def __init__(self, db_path: Path = Path.home() / ".cortex" / "pulmones.db"):
        self.db_path = db_path
        self.running = False
        # Para evitar saturar APIs en la recuperación, aplicamos rate-limiting por lote
        self.batch_size = 5 
        
    def _fetch_ripe_tasks(self) -> list:
        """O(1) fetch gracias al índice idx_next_retry."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, target_func, payload, retries 
                FROM fallback_queue 
                WHERE next_retry_at <= ? 
                ORDER BY next_retry_at ASC 
                LIMIT ?
                """,
                (now, self.batch_size)
            )
            return [dict(row) for row in cursor.fetchall()]

    def _remove_task(self, task_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM fallback_queue WHERE id = ?", (task_id,))

    def _penalize_task(self, task_id: int, retries: int):
        """Exponential backoff para tareas crónicamente fallidas."""
        new_retries = retries + 1
        # Backoff: 1m, 2m, 4m, 8m... max 60 min.
        delay = min(60 * (2 ** retries), 3600) 
        next_retry = time.time() + delay
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE fallback_queue SET retries = ?, next_retry_at = ? WHERE id = ?",
                (new_retries, next_retry, task_id)
            )
        logger.warning("⏳ Tarea %s penalizada. Reintento %s en %ss.", task_id, new_retries, delay)

    async def _resolve_target(self, target_func_path: str):
        """
        Resuelve dinámicamente el string de la función guardado en SQLite.
        """
        module_path, func_name = target_func_path.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, func_name)

    async def _execute_task(self, task: dict):
        task_id = task['id']
        payload = json.loads(task['payload'])
        
        try:
            func = await self._resolve_target(task['target_func'])
            logger.info("🔄 Re-ejecutando %s [ID: %s]...", task['target_func'], task_id)
            
            args = payload.get('args', [])
            kwargs = payload.get('kwargs', {})
            
            await func(*args, **kwargs)
            
            # Éxito de la operación. Eliminamos la impureza de la BD.
            self._remove_task(task_id)
            logger.info("✅ Tarea %s recuperada exitosamente.", task_id)
            
        except Exception as e:
            logger.error("❌ Fallo crónico en tarea %s: %s", task_id, str(e))
            self._penalize_task(task_id, task['retries'])

    async def start_loop(self, poll_interval: float = 30.0):
        """El corazón del Submarino. Late cada `poll_interval` segundos."""
        self.running = True
        logger.info("🫁 [WORKER] PULMONES Daemon iniciado. Escaneando hipoxia de red...")
        
        while self.running:
            try:
                tasks = self._fetch_ripe_tasks()
                if tasks:
                    logger.info("📥 Encontradas %s tareas maduras para reintento.", len(tasks))
                    # Ejecución concurrente del lote
                    await asyncio.gather(*(self._execute_task(t) for t in tasks))
                else:
                    logger.debug("O₂ levels optimal. No tasks pending.")
            except Exception as e:
                logger.critical("💀 [WORKER] Fallo sistémico en el bucle principal: %s", str(e))
            
            await asyncio.sleep(poll_interval)

if __name__ == "__main__":
    worker = PulmonesWorker()
    try:
        asyncio.run(worker.start_loop())
    except KeyboardInterrupt:
        logger.info("🛑 [WORKER] Recibida señal de apagado. Respiración artificial detenida.")
