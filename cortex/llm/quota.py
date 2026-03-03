"""CORTEX v6.2 — Sovereign Quota Manager.

Implementa el Protocolo PULMONES (rate-limiting inter-proceso) utilizando
SQLite WAL para sincronización de latencia cero. Previene estrangulamiento
429 (Too Many Requests) al gestionar un Token Bucket distribuido con
backoff exponencial y métricas integradas.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import secrets
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.llm.quota")

# Module-level CSPRNG — avoid recreating per-iteration (~0.5ms saved/call)
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


@dataclasses.dataclass(frozen=True, slots=True)
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
        db_path: str = "~/.cortex/quota.db",
        capacity: int = 5,  # Reducido de 15 a 5 para evitar burst limit (429)
        refill_rate: float = 0.15,  # ~9 tokens / 60s (más conservador)
    ) -> None:
        self.db_path = Path(db_path).expanduser()
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._init_db()

    # ─── Internals ────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with _db(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_quotas (
                    provider      TEXT PRIMARY KEY,
                    tokens        REAL    NOT NULL,
                    last_update   REAL    NOT NULL,
                    acquired      INTEGER NOT NULL DEFAULT 0,
                    throttled     INTEGER NOT NULL DEFAULT 0,
                    timeouts      INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            # Legacy fallback if needed (leave it around for safety)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quota_bucket (
                    id            INTEGER PRIMARY KEY,
                    tokens        REAL    NOT NULL, last_update REAL NOT NULL,
                    acquired INTEGER NOT NULL DEFAULT 0, throttled INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def _init_provider(self, provider: str) -> None:
        with _db(self.db_path) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO provider_quotas
                   (provider, tokens, last_update, acquired, throttled, timeouts)
                   VALUES (?, ?, ?, 0, 0, 0)""",
                (provider, self.capacity, time.time()),
            )

    def _consume_sync(self, provider: str, tokens: int) -> float:
        """Intenta consumir tokens atómicamente."""
        if tokens < 1:
            raise ValueError(f"tokens must be >= 1, got {tokens}")
        now = time.time()
        try:
            with _db(self.db_path, exclusive=True) as conn:
                row = conn.execute(
                    "SELECT tokens, last_update FROM provider_quotas WHERE provider = ?",
                    (provider,),
                ).fetchone()

                if not row:
                    self._init_provider(provider)
                    row = (self.capacity, now)

                current_tokens, last_update = row

                refilled = min(
                    self.capacity,
                    current_tokens + (now - last_update) * self.refill_rate,
                )

                if refilled >= tokens:
                    conn.execute(
                        """UPDATE provider_quotas
                           SET tokens = ?, last_update = ?, acquired = acquired + 1
                           WHERE provider = ?""",
                        (refilled - tokens, now, provider),
                    )
                    return 0.0

                deficit = tokens - refilled
                wait = deficit / self.refill_rate
                conn.execute(
                    "UPDATE provider_quotas SET throttled = throttled + 1 WHERE provider = ?",
                    (provider,),
                )
                return wait

        except sqlite3.OperationalError:
            return 0.5  # DB contendida — backoff corto

    # ─── Public API ───────────────────────────────────────────────────

    async def acquire(
        self, provider: str = "default", tokens: int = 1, deadline: float = 120.0
    ) -> bool:
        """Adquiere tokens asíncronamente siguiendo el Protocolo PULMONES.

        Usa backoff exponencial con jitter para prevenir thundering-herd
        cuando múltiples procesos compiten por el mismo bucket.

        Args:
            provider: Identificador del proveedor a estrangular.
            tokens:   Tokens a consumir (1 = 1 API request).
            deadline: Tiempo máximo de espera total en segundos.

        Returns:
            True si se adquirió la cuota, False si expiró el deadline.
        """
        start = time.time()
        attempt = 0

        while True:
            wait = self._consume_sync(provider, tokens)

            if wait <= 0:
                return True

            elapsed = time.time() - start
            if elapsed >= deadline:
                logger.error(
                    "PULMONES [%s]: Timeout tras %.1fs esperando %d tokens.",
                    provider,
                    elapsed,
                    tokens,
                )
                self._increment_timeouts(provider)
                return False

            # Hardware Entropy + Golden Ratio (Caos termodinámico asimétrico profundo)
            jitter = _RNG.uniform(0.1, 1.618 ** min(attempt + 1, 6))
            sleep = min(wait, 2 ** min(attempt, 5)) + jitter
            sleep = min(sleep, deadline - elapsed)  # nunca sobrepasar el deadline

            logger.info(
                "PULMONES [%s]: Estrangulado. Exhalando %.2fs (intento %d)…",
                provider,
                sleep,
                attempt + 1,
            )
            await asyncio.sleep(sleep)
            attempt += 1

    def bankrupt(self, provider: str, penalty_seconds: float = 0.0) -> None:
        """Vacía el cubo de un proveedor y opcionalmente aplica una penalización térmica."""
        now = time.time()
        tokens = -(penalty_seconds * self.refill_rate)
        try:
            with _db(self.db_path, exclusive=True) as conn:
                conn.execute(
                    """UPDATE provider_quotas
                       SET tokens = ?, last_update = ?
                       WHERE provider = ?""",
                    (tokens, now, provider),
                )
            logger.warning(
                "PULMONES [%s]: Bankrupt! Tokens drained to %.1f (Penalty: %.1fs).",
                provider,
                tokens,
                penalty_seconds,
            )
        except sqlite3.OperationalError:
            pass

    def status(self, provider: str = "default") -> QuotaStatus:
        """Estado completo del bucket con métricas de observabilidad."""
        now = time.time()
        with _db(self.db_path) as conn:
            row = conn.execute(
                "SELECT tokens, last_update, acquired, throttled, timeouts "
                "FROM provider_quotas WHERE provider = ?",
                (provider,),
            ).fetchone()

        if not row:
            self._init_provider(provider)
            current_tokens, last_update, acquired, throttled, timeouts = self.capacity, now, 0, 0, 0
        else:
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

    def reset(self, provider: str = "default") -> None:
        """Reset de emergencia: llena el bucket al máximo y borra métricas."""
        with _db(self.db_path, exclusive=True) as conn:
            conn.execute(
                """UPDATE provider_quotas
                   SET tokens = ?, last_update = ?, acquired = 0, throttled = 0, timeouts = 0
                   WHERE provider = ?""",
                (self.capacity, time.time(), provider),
            )
        logger.warning(
            "PULMONES [%s]: Bucket reseteado a capacidad máxima (%s tokens).",
            provider,
            self.capacity,
        )

    def _increment_timeouts(self, provider: str) -> None:
        try:
            with _db(self.db_path) as conn:
                conn.execute(
                    "UPDATE provider_quotas SET timeouts = timeouts + 1 WHERE provider = ?",
                    (provider,),
                )
        except sqlite3.OperationalError:
            pass
