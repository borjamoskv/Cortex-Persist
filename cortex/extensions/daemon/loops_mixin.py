# pyright: reportAttributeAccessIssue=false
"""Background loop methods for MoskvDaemon (Seal 8 LOC extraction)."""

from __future__ import annotations

import asyncio
import logging
import threading
import time

from cortex.extensions.daemon.models import DaemonStatus

logger = logging.getLogger("moskv-daemon")


class LoopsMixin:
    """Mixin providing daemon background thread loop methods."""

    def _spawn_thread(self, target, name: str) -> None:
        """Spawn a daemon thread and track it."""
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def _run_neural_loop(self) -> None:
        """Fast polling loop for zero-latency neural intent ingestion."""
        logger.info("🧠 Neural-Bandwidth Sync thread started (1Hz)")
        while not self._shutdown:
            try:
                alerts = self.neural_monitor.check()
                if alerts:
                    self._alert_neural(alerts)
            except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
                logger.debug("Neural loop error: %s", e)
            self._stop_event.wait(timeout=1.0)

    def _run_ast_oracle_loop(self) -> None:
        """Runs the AST Oracle event loop."""
        logger.info("👁️ AST Oracle thread started")

        async def _lifecycle():
            task = asyncio.create_task(self.ast_oracle.start())
            while not self._shutdown:
                await asyncio.sleep(1.0)
            await self.ast_oracle.stop()
            await task

        try:
            asyncio.run(_lifecycle())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("AST Oracle loop error: %s", e)

    def _run_heartbeat_loop(self) -> None:
        """Runs the HeartbeatDaemon event loop."""
        if not self.heartbeat_daemon:
            return
        logger.info("❤️  Heartbeat thread started")

        async def _lifecycle():
            task = asyncio.create_task(self.heartbeat_daemon.start())
            while not self._shutdown:
                await asyncio.sleep(1.0)
            await self.heartbeat_daemon.stop()
            await task

        try:
            asyncio.run(_lifecycle())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Heartbeat loop error: %s", e)

    def _run_entropic_wake_loop(self) -> None:
        """Runs the Entropic Wake Daemon event loop."""
        logger.info("🌌 Entropic Wake thread started")
        try:
            self.entropic_wake_daemon.run_loop()
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Entropic Wake loop error: %s", e)

    def _run_sentinel_oracle_loop(self) -> None:
        """Runs the Sentinel Oracle polling loop."""
        logger.info("🛡️ CORTEX Sentinel Oracle thread started")
        try:
            asyncio.run(self.sentinel_oracle.run_loop())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Sentinel Oracle loop error: %s", e)

    def _run_frontier_loop(self) -> None:
        """Runs the Frontier Daemon event loop."""
        logger.info("🚀 Frontier thread started")
        try:
            asyncio.run(self.frontier_daemon.run_loop())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Frontier loop error: %s", e)

    def _run_iot_oracle_loop(self) -> None:
        """Runs the IoT Oracle event loop for physical entanglement."""
        logger.info("📡 IoT Oracle thread started")

        async def _lifecycle():
            task = asyncio.create_task(self.iot_oracle.start())
            while not self._shutdown:
                await asyncio.sleep(1.0)
            await self.iot_oracle.stop()
            await task

        try:
            asyncio.run(_lifecycle())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("IoT Oracle loop error: %s", e)

    def _run_zero_prompting_loop(self) -> None:
        """Runs the Zero-Prompting Evolution Daemon event loop."""
        logger.info("🧠 Zero-Prompting thread started")
        try:
            asyncio.run(self.zero_prompting_daemon.run_loop())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Zero-Prompting loop error: %s", e)

    def _run_epistemic_breaker_loop(self) -> None:
        """Runs the Epistemic Circuit Breaker Daemon event loop."""
        logger.info("🛡️ Epistemic Breaker thread started")
        try:
            asyncio.run(self.epistemic_breaker_daemon.run())
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            logger.error("Epistemic Breaker loop error: %s", e)

    def _auto_sync(self, status: DaemonStatus) -> None:
        """Automatic memory JSON ↔ CORTEX DB synchronization."""
        if not self._shared_engine:
            return
        try:
            from cortex.extensions.sync import export_snapshot, export_to_json, sync_memory

            async def _run_sync():
                s_res = await sync_memory(self._shared_engine)
                w_res = await export_to_json(self._shared_engine)
                await export_snapshot(self._shared_engine)
                return s_res, w_res

            sync_result, wb_result = asyncio.run(_run_sync())
            if sync_result.had_changes:
                logger.info("Sync: %d facts synced", sync_result.total)
            if wb_result.had_changes:
                logger.info(
                    "Write-back: %d files, %d items",
                    wb_result.files_written,
                    wb_result.items_exported,
                )
        except Exception as e:  # noqa: BLE001 — top-level loop crash barrier
            status.errors.append(f"Memory sync error: {e}")
            logger.exception("Memory sync failed")

    def _flush_timer(self) -> None:
        """Flush timing tracker if available."""
        tracker = getattr(self, "tracker", None)
        if tracker:
            try:
                tracker.flush()
            except (ValueError, KeyError, OSError, RuntimeError, AttributeError):  # noqa: BLE001 — tracker flush is best-effort
                pass

    def _should_alert(self, key: str) -> bool:
        """Rate-limit duplicate alerts."""
        if not self.notify_enabled:
            return False
        now = time.monotonic()
        last = self._last_alerts.get(key, 0)
        if now - last < self._cooldown:
            return False
        self._last_alerts[key] = now
        return True

    def _run_health_loop(self) -> None:
        """Periodic health monitoring via Health Index."""
        logger.info("🏥 Health Monitor thread started (5min interval)")

        from cortex.extensions.daemon.health_loop import HealthLoop

        db_path = ""
        if self._shared_engine:
            db_path = str(getattr(self._shared_engine, "_db_path", ""))

        health = HealthLoop(
            db_path=db_path,
            notify_fn=(self._send_notification if hasattr(self, "_send_notification") else None),
        )

        base_interval = 300.0
        max_interval = 3600.0
        current_interval = base_interval

        while not self._shutdown:
            try:
                data = health.tick()
                if data is None:
                    # tick() failed (returns None on internal exception)
                    current_interval = min(current_interval * 2, max_interval)
                    logger.warning(
                        "Health check failed. Backing off to %.1fs",
                        current_interval,
                    )
                else:
                    # Success resets backoff
                    if current_interval > base_interval:
                        logger.info(
                            "Health check recovered. Resetting interval to %.1fs", base_interval
                        )
                    current_interval = base_interval
                    if self._shared_engine:
                        health.persist_snapshot(self._shared_engine, data)
            except Exception as e:  # noqa: BLE001 — safety net
                current_interval = min(current_interval * 2, max_interval)
                logger.error(
                    "Health loop critical error: %s. Backing off to %.1fs", e, current_interval
                )

            self._stop_event.wait(timeout=current_interval)
