from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import Any

from cortex.engine.circuit_breaker import CircuitBreaker, CircuitState  # noqa: F401 — re-exported

logger = logging.getLogger("CORTEX.PULMONES")


class PulmonesQueue:
    """Cola SQLite ACID para persistir tareas fallidas (Zero-Trust Queue)."""

    def __init__(self, db_path: Path = Path.home() / ".cortex" / "pulmones.db"):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fallback_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_func TEXT NOT NULL,
                    payload JSON NOT NULL,
                    retries INTEGER DEFAULT 0,
                    next_retry_at REAL NOT NULL
                )
            """)
            # Índice para O(1) fetch de la próxima tarea
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_next_retry ON fallback_queue(next_retry_at)"
            )

    def enqueue(self, func_name: str, args: tuple, kwargs: dict, delay: float = 60.0) -> None:
        payload = json.dumps({"args": args, "kwargs": kwargs})
        next_retry = time.time() + delay
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO fallback_queue (target_func, payload, next_retry_at) VALUES (?, ?, ?)",
                (func_name, payload, next_retry),
            )
            logger.warning(
                "🫁 [PULMONES] Payload encolado para %s. Reintento en %ss.", func_name, delay
            )


def sovereign_circuit_breaker(timeout: float = 10.0, max_retries: int = 2, threshold: int = 3):
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
                logger.warning(
                    "🛡️ [PULMONES] Circuito Abierto. Bloqueando llamada a %s", func.__name__
                )
                queue.enqueue(target_name, args, kwargs)
                return {"status": "queued", "reason": "circuit_open"}

            for attempt in range(max_retries + 1):
                try:
                    # Timeout estricto para no bloquear el agente
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    cb.record_success()
                    return {"status": "success", "data": result}

                except (asyncio.TimeoutError, ConnectionError) as e:
                    logger.error(
                        "⚡ [PULMONES] Intento %s fallido en %s: %s",
                        attempt + 1,
                        func.__name__,
                        str(e),
                    )
                    if attempt == max_retries:
                        cb.record_failure()
                        queue.enqueue(target_name, args, kwargs)
                        return {"status": "queued", "reason": "max_retries_exceeded"}
                    await asyncio.sleep(2**attempt)  # Exponential backoff

                except Exception as e:  # noqa: BLE001
                    # Ω₃: Excepciones de negocio/código no activan el CB — sólo timeouts/red
                    logger.critical(
                        "💀 [PULMONES] Falla interna no recuperable en %s: %s",
                        func.__name__,
                        str(e),
                    )
                    raise e

        return wrapper

    return decorator
