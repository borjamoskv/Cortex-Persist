# [C5-REAL] Exergy-Maximized
import asyncio
import logging
import os

from cortex.database.core import connect_async_ctx

logger = logging.getLogger(__name__)


class EntropyDaemon:
    """
    [C5-REAL] Daemon de Higiene Termodinámica.
    Separa la Supervivencia (ExergyDaemon) del Mantenimiento (EntropyDaemon).
    Su función es reclamar el espacio físico en disco (Vacío, WAL truncation, Fragmentación).
    Opera en un thread asíncrono secundario y ejecuta VACUUM con mínima interrupción I/O.
    """

    def __init__(self, db_path: str, scan_interval: int = 600):
        self.db_path = db_path
        self.interval = scan_interval
        self._running = False
        self._task = None

    async def _daemon_loop(self):
        logger.info("[EntropyDaemon] Activo. Gestión de basuras de SQLite iniciada.")
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                await self._hygiene_sweep()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[P0] Untracked Exception en EntropyDaemon")

    async def _hygiene_sweep(self):
        """Reclama espacio físico devolviéndolo al OS."""
        logger.info("[EntropyDaemon] Ejecutando VACUUM e higiene WAL...")
        db_size_before = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        async with connect_async_ctx(self.db_path) as conn:
            # Checkpoint the Write-Ahead Log (WAL) to database file and truncate WAL
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            # Reclaim empty pages back to OS
            await conn.execute("VACUUM;")

        db_size_after = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        recovered = (db_size_before - db_size_after) / 1024

        if recovered > 0:
            logger.info(f"[EntropyDaemon] Limpieza exitosa. Espacio recuperado: {recovered:.2f} KB")

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
            logger.info("[EntropyDaemon] Terminado.")
