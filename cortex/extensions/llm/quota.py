# [C5-REAL] Exergy-Maximized
"""Sovereign Quota Manager.

Implementa el Protocolo PULMONES (rate-limiting inter-proceso) utilizando
SQLite WAL para sincronización de latencia cero. Previene estrangulamiento
429 (Too Many Requests) al gestionar un Token Bucket distribuido con
backoff exponencial y métricas integradas.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import os
import secrets
import sqlite3
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.extensions.llm.quota")

# Module-level CSPRNG - avoid recreating per-iteration (~0.5ms saved/call)
_RNG = secrets.SystemRandom()


@contextmanager
def _db(path: Path, exclusive: bool = False) -> Generator[sqlite3.Connection, None, None]:
    """Context manager soberano para conexiones SQLite via CORTEX factory."""
    conn = db_connect(str(path), timeout=5)
    try:
        if exclusive:
            conn.execute("BEGIN EXCLUSIVE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@dataclasses.dataclass(frozen=True)
class QuotaStatus:
    """Typed snapshot of the quota bucket state."""

    capacity: float
    current_tokens: float
    fill_pct: float
    refill_rate_per_s: float
    time_to_full_s: float
    acquired: int
    throttled: int
    timeouts: int
    throttle_ratio_pct: float

    def __repr__(self) -> str:
        return (
            f"QuotaStatus({self.current_tokens:.1f}/{self.capacity:.0f} "
            f"[{self.fill_pct}%] | acq={self.acquired} thr={self.throttled} "
            f"to={self.timeouts})"
        )


class SovereignQuotaManager:
    """Token Bucket atómico sobre SQLite WAL.

    Características:
    - O(1) sincronización inter-proceso (SQLite WAL + EXCLUSIVE lock)
    - Backoff exponencial con jitter anti thundering-herd
    - Métricas integradas de observabilidad en tiempo real
    - Reset manual de emergencia
    """

    def __init__(
        self,
        db_path: str | None = None,
        capacity: int = 10,
        refill_rate: float | None = None,
    ) -> None:
        configured_path = db_path or os.environ.get("CORTEX_LLM_QUOTA_DB", "~/.cortex/quota.db")
        self.db_path = Path(configured_path).expanduser()
        self.capacity = float(capacity)

        # ── Protocolo PULMONES Conservative Refill ──
        # Prioritize ENV > Explicit arg > 10 RPM Default
        env_max_rpm = os.environ.get("CORTEX_LLM_MAX_RPM")
        if env_max_rpm:
            self.refill_rate = float(env_max_rpm) / 60.0
        elif refill_rate is not None:
            self.refill_rate = float(refill_rate)
        else:
            self.refill_rate = 10.0 / 60.0  # 10 RPM (0.166 t/s) - swarm baseline

        self._init_db()

    # ─── Internals ────────────────────────────────────────────────────

    def _init_db(self) -> None:
        candidates = [self.db_path]
        fallback = Path(tempfile.gettempdir()) / "cortex_llm_quota.db"
        if fallback not in candidates:
            candidates.append(fallback)

        last_error: sqlite3.OperationalError | None = None
        for candidate in candidates:
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                with _db(candidate) as conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS quota_bucket (
                            id            INTEGER PRIMARY KEY,
                            tokens        REAL    NOT NULL,
                            last_update   REAL    NOT NULL,
                            acquired      INTEGER NOT NULL DEFAULT 0,
                            throttled     INTEGER NOT NULL DEFAULT 0,
                            timeouts      INTEGER NOT NULL DEFAULT 0
                        )
                        """
                    )
                    cursor = conn.execute("SELECT COUNT(*) FROM quota_bucket")
                    if cursor.fetchone()[0] == 0:
                        conn.execute(
                            """INSERT INTO quota_bucket
                               (id, tokens, last_update, acquired, throttled, timeouts)
                               VALUES (1, ?, ?, 0, 0, 0)""",
                            (self.capacity, time.monotonic()),
                        )
                if candidate != self.db_path:
                    logger.warning(
                        "LLM quota DB unavailable at %s; falling back to %s",
                        self.db_path,
                        candidate,
                    )
                    self.db_path = candidate
                return
            except sqlite3.OperationalError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

    def _consume_sync(self, tokens: int) -> float:
        """Intenta consumir tokens atómicamente.

        Args:
            tokens: Number of tokens to consume (must be >= 1).

        Returns:
            0.0  → consumo exitoso.
            > 0  → segundos de espera estimados.
        """
        if tokens < 1:
            raise ValueError(f"tokens must be >= 1, got {tokens}")
        now = time.monotonic()
        try:
            with _db(self.db_path, exclusive=True) as conn:
                row = conn.execute(
                    "SELECT tokens, last_update FROM quota_bucket WHERE id = 1"
                ).fetchone()
                current_tokens, last_update = row

                refilled = min(
                    self.capacity,
                    current_tokens + (now - last_update) * self.refill_rate,
                )

                if refilled >= tokens:
                    conn.execute(
                        """UPDATE quota_bucket
                           SET tokens = ?, last_update = ?, acquired = acquired + 1
                           WHERE id = 1""",
                        (refilled - tokens, now),
                    )
                    return 0.0

                deficit = tokens - refilled
                wait = deficit / self.refill_rate
                conn.execute("UPDATE quota_bucket SET throttled = throttled + 1 WHERE id = 1")
                return wait

        except sqlite3.OperationalError:
            return 0.5  # DB contendida - backoff corto

    # ─── Public API ───────────────────────────────────────────────────

    async def acquire(self, tokens: int = 1, deadline: float = 120.0) -> bool:
        """Adquiere tokens asíncronamente siguiendo el Protocolo PULMONES.

        Usa backoff exponencial con jitter para prevenir thundering-herd
        cuando múltiples procesos compiten por el mismo bucket.

        Args:
            tokens:   Tokens a consumir (1 = 1 API request).
            deadline: Tiempo máximo de espera total en segundos.

        Returns:
            True si se adquirió la cuota, False si expiró el deadline.
        """
        start = time.monotonic()
        attempt = 0

        while True:
            wait = self._consume_sync(tokens)

            if wait <= 0:
                return True

            elapsed = time.monotonic() - start
            if elapsed >= deadline:
                logger.error("PULMONES: Timeout tras %.1fs esperando %d tokens.", elapsed, tokens)
                self._increment_timeouts()
                return False

            # Hardware Entropy + Golden Ratio (Caos termodinámico asimétrico profundo)
            jitter = _RNG.uniform(0.1, 1.618 ** min(attempt + 1, 6))
            sleep = min(wait, 2 ** min(attempt, 5)) + jitter
            sleep = min(sleep, deadline - elapsed)  # nunca sobrepasar el deadline

            logger.info("PULMONES: Estrangulado. Exhalando %.2fs (intento %d)…", sleep, attempt + 1)
            await asyncio.sleep(sleep)
            attempt += 1

    def status(self) -> QuotaStatus:
        """Estado completo del bucket con métricas de observabilidad."""
        now = time.monotonic()
        with _db(self.db_path) as conn:
            row = conn.execute(
                "SELECT tokens, last_update, acquired, throttled, timeouts "
                "FROM quota_bucket WHERE id = 1"
            ).fetchone()
        current_tokens, last_update, acquired, throttled, timeouts = row
        current = min(
            self.capacity,
            current_tokens + (now - last_update) * self.refill_rate,
        )
        total = acquired + throttled or 1
        return QuotaStatus(
            capacity=self.capacity,
            current_tokens=round(current, 2),
            fill_pct=round((current / self.capacity) * 100, 1),
            refill_rate_per_s=self.refill_rate,
            time_to_full_s=round(max(0, (self.capacity - current) / self.refill_rate), 2),
            acquired=acquired,
            throttled=throttled,
            timeouts=timeouts,
            throttle_ratio_pct=round((throttled / total) * 100, 1),
        )

    def reset(self) -> None:
        """Reset de emergencia: llena el bucket al máximo y borra métricas."""
        with _db(self.db_path, exclusive=True) as conn:
            conn.execute(
                """UPDATE quota_bucket
                   SET tokens = ?, last_update = ?, acquired = 0, throttled = 0, timeouts = 0
                   WHERE id = 1""",
                (self.capacity, time.monotonic()),
            )
        logger.warning("PULMONES: Bucket reseteado a capacidad máxima (%s tokens).", self.capacity)

    def _increment_timeouts(self) -> None:
        try:
            with _db(self.db_path) as conn:
                conn.execute("UPDATE quota_bucket SET timeouts = timeouts + 1 WHERE id = 1")
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)
