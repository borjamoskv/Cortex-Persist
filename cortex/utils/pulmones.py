from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import tempfile
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import Any

logger = logging.getLogger("CORTEX.PULMONES")


class PulmonesQueue:
    """Cola SQLite ACID para persistir tareas fallidas (Zero-Trust Queue)."""

    def __init__(self, db_path: Path = Path.home() / ".cortex" / "pulmones.db"):
        self.db_path = db_path
        self._fallback_path = Path(tempfile.gettempdir()) / "cortex_pulmones.db"
        self._available = True
        try:
            self._init_with_fallback()
        except (OSError, sqlite3.Error) as exc:
            self._available = False
            logger.warning("🫁 [PULMONES] Queue disabled: %s", exc)

    def _init_with_fallback(self) -> None:
        candidates = [self.db_path]
        if self._fallback_path not in candidates:
            candidates.append(self._fallback_path)

        last_error: OSError | sqlite3.Error | None = None
        for candidate in candidates:
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                self._init_db_at(candidate)
                if candidate != self.db_path:
                    logger.warning(
                        "🫁 [PULMONES] Primary DB unavailable at %s; falling back to %s",
                        self.db_path,
                        candidate,
                    )
                    self.db_path = candidate
                return
            except (OSError, sqlite3.Error) as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

    def _init_db_at(self, path: Path) -> None:
        with sqlite3.connect(path) as conn:
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
        if not self._available:
            logger.warning("🫁 [PULMONES] Queue unavailable, dropping payload for %s.", func_name)
            return
        payload = json.dumps({"args": args, "kwargs": kwargs})
        next_retry = time.time() + delay
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO fallback_queue (target_func, payload, next_retry_at) VALUES (?, ?, ?)",
                    (func_name, payload, next_retry),
                )
                logger.warning(
                    "🫁 [PULMONES] Payload encolado para %s. Reintento en %ss.",
                    func_name,
                    delay,
                )
        except sqlite3.Error:
            if self.db_path != self._fallback_path:
                try:
                    self._init_db_at(self._fallback_path)
                    self.db_path = self._fallback_path
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "INSERT INTO fallback_queue (target_func, payload, next_retry_at) VALUES (?, ?, ?)",
                            (func_name, payload, next_retry),
                        )
                    logger.warning(
                        "🫁 [PULMONES] Primary queue readonly; payload for %s enqueued via fallback DB.",
                        func_name,
                    )
                    return
                except sqlite3.Error as fallback_exc:
                    exc = fallback_exc
            self._available = False
            logger.warning("🫁 [PULMONES] Queue disabled during enqueue: %s", exc)


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
        return True  # HALF_OPEN permite 1 intento


def sovereign_circuit_breaker(timeout: float = 10.0, max_retries: int = 2, threshold: int = 3):
    """
    Decorador Mágico:
    1. Limita el tiempo de ejecución (asyncio.wait_for).
    2. Corta el circuito si la API destino está caída.
    3. Si falla tras `max_retries`, cae graciosamente a la cola SQLite (PulmonesQueue).
    """
    cb = CircuitBreaker(failure_threshold=threshold)
    queue: PulmonesQueue | None = None

    def _get_queue() -> PulmonesQueue | None:
        nonlocal queue
        if queue is not None:
            return queue
        try:
            queue = PulmonesQueue()
        except OSError as exc:
            logger.warning("🫁 [PULMONES] Queue unavailable, dropping fallback enqueue: %s", exc)
            queue = None
        return queue

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            target_name = f"{func.__module__}.{func.__name__}"
            if not cb.can_execute():
                logger.warning(
                    "🛡️ [PULMONES] Circuito Abierto. Bloqueando llamada a %s", func.__name__
                )
                q = _get_queue()
                if q is not None:
                    q.enqueue(target_name, args, kwargs)
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
                        q = _get_queue()
                        if q is not None:
                            q.enqueue(target_name, args, kwargs)
                        return {"status": "queued", "reason": "max_retries_exceeded"}
                    await asyncio.sleep(2**attempt)  # Exponential backoff

                except Exception as e:  # noqa: BLE001
                    # Ω₃: Excepciones de negocio o código no activan el circuit breaker, solo timeouts/red
                    logger.critical(
                        "💀 [PULMONES] Falla interna no recuperable en %s: %s",
                        func.__name__,
                        str(e),
                    )
                    raise e

        return wrapper

    return decorator
