import asyncio
import sqlite3
import time
import json
import logging
from typing import Callable, Any, Awaitable, Optional
from functools import wraps
from pathlib import Path

logger = logging.getLogger("CORTEX.PULMONES")

class PulmonesQueue:
    """Cola SQLite ACID para persistir tareas fallidas (Zero-Trust Queue)."""
    def __init__(self, db_path: Path = Path.home() / ".cortex" / "pulmones.db"):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fallback_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_func TEXT NOT NULL,
                    payload JSON NOT NULL,
                    retries INTEGER DEFAULT 0,
                    next_retry_at REAL NOT NULL
                )
            ''')
            # Índice para O(1) fetch de la próxima tarea
            conn.execute('CREATE INDEX IF NOT EXISTS idx_next_retry ON fallback_queue(next_retry_at)')

    def enqueue(self, func_name: str, args: tuple, kwargs: dict, delay: float = 60.0) -> None:
        payload = json.dumps({"args": args, "kwargs": kwargs})
        next_retry = time.time() + delay
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO fallback_queue (target_func, payload, next_retry_at) VALUES (?, ?, ?)",
                (func_name, payload, next_retry)
            )
            logger.warning("🫁 [PULMONES] Payload encolado para %s. Reintento en %ss.", func_name, delay)

class CircuitBreaker:
    """Implementa estados Closed, Open, Half-Open para proteger el Event Loop."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
        self.last_failure_time = 0.0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error("🔌 [PULMONES] Circuit Breaker ABIERTO. Fallos: %s", self.failure_count)

    def record_success(self):
        if self.state != "CLOSED":
            logger.info("🔌 [PULMONES] Circuit Breaker CERRADO. Conexión restaurada.")
        self.failure_count = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("🔌 [PULMONES] Circuit Breaker HALF-OPEN. Probando conexión...")
                return True
            return False
        return True # HALF_OPEN permite 1 intento

def sovereign_circuit_breaker(
    timeout: float = 10.0, 
    max_retries: int = 2,
    threshold: int = 3
):
    """
    Decorador Mágico: 
    1. Limita el tiempo de ejecución (asyncio.wait_for).
    2. Corta el circuito si la API destino está caída.
    3. Si falla tras `max_retries`, cae graciosamente a la cola SQLite (PulmonesQueue).
    """
    cb = CircuitBreaker(failure_threshold=threshold)
    queue = PulmonesQueue()

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            target_name = f"{func.__module__}.{func.__name__}"
            if not cb.can_execute():
                logger.warning("🛡️ [PULMONES] Circuito Abierto. Bloqueando llamada a %s", func.__name__)
                queue.enqueue(target_name, args, kwargs)
                return {"status": "queued", "reason": "circuit_open"}

            for attempt in range(max_retries + 1):
                try:
                    # Timeout estricto para no bloquear el agente
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    cb.record_success()
                    return {"status": "success", "data": result}
                
                except (asyncio.TimeoutError, ConnectionError) as e:
                    logger.error("⚡ [PULMONES] Intento %s fallido en %s: %s", attempt+1, func.__name__, str(e))
                    if attempt == max_retries:
                        cb.record_failure()
                        queue.enqueue(target_name, args, kwargs)
                        return {"status": "queued", "reason": "max_retries_exceeded"}
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                
                except Exception as e:
                    # Ω₃: Excepciones de negocio o código no activan el circuit breaker, solo timeouts/red
                    logger.critical("💀 [PULMONES] Falla interna no recuperable en %s: %s", func.__name__, str(e))
                    raise e
                    
        return wrapper
    return decorator
