# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from typing import Any

# pyright: reportAttributeAccessIssue=false
"""Background loop methods for MoskvDaemon (Seal 8 LOC extraction)."""


import asyncio
import logging
import threading
import time

from cortex.extensions.daemon.models import DaemonStatus

logger = logging.getLogger("moskv-daemon")


class LoopsMixin:
    tracker: Any
    site_monitor: Any
    ghost_watcher: Any
    memory_syncer: Any
    neural_monitor: Any
    _threads: list[threading.Thread]

    def _alert_neural(self, alerts: list) -> None: ...

    cert_monitor: Any
    engine_health: Any
    disk_monitor: Any
    evaluation_monitor: Any
    auto_mejoralo: Any
    compaction_monitor: Any
    perception_monitor: Any
    security_monitor: Any
    signal_monitor: Any
    cloud_sync_monitor: Any
    tombstone_monitor: Any
    workflow_monitor: Any
    epistemic_monitor: Any
    aether_monitor: Any
    _aether_daemon: Any
    fiat_oracle: Any
    ast_oracle: Any
    heartbeat_daemon: Any
    entropic_wake_daemon: Any
    sentinel_oracle: Any
    frontier_daemon: Any
    iot_oracle: Any
    zero_prompting_daemon: Any
    epistemic_breaker_daemon: Any
    notify_enabled: bool
    _last_alerts: dict[str, float]
    _cooldown: float
    _shared_engine: Any
    scheduler: Any
    watchdog_hub: Any
    callback_api: Any
    _shutdown: bool
    _stop_event: Any

    """Mixin providing daemon background thread loop methods."""

    async def _run_lifecycle_daemon_async(self, daemon: Any, name: str, emoji: str) -> None:
        """Runs a daemon with start/stop lifecycle as an async task."""
        if not daemon:
            return
        logger.info("%s %s task started", emoji, name)
        task = asyncio.create_task(daemon.start())
        while not self._shutdown:
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
        await daemon.stop()
        await task

    async def _run_loop_daemon_async(
        self, daemon: Any, name: str, emoji: str, run_method: str = "run_loop"
    ) -> None:
        """Runs a daemon's run_loop/run method as an async task."""
        if not daemon:
            return
        logger.info("%s %s task started", emoji, name)
        try:
            method = getattr(daemon, run_method)
            res = method()
            if asyncio.iscoroutine(res):
                await res
        except Exception as e:  # noqa: BLE001
            logger.error("%s loop error: %s", name, e)

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

    async def _run_neural_loop_async(self) -> None:
        """Fast polling loop for zero-latency neural intent ingestion (Async)."""
        logger.info("🧠 Neural-Bandwidth Sync task started (1Hz)")
        while not self._shutdown:
            try:
                alerts = await asyncio.to_thread(self.neural_monitor.check)
                if alerts:
                    self._alert_neural(alerts)
            except Exception as e:  # noqa: BLE001
                logger.debug("Neural loop error: %s", e)
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break

    async def _run_health_loop_async(self) -> None:
        """Periodic health monitoring via Health Index (Async)."""
        logger.info("🏥 Health Monitor task started (5min interval)")

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
                data = await asyncio.to_thread(health.tick)
                if data is None:
                    current_interval = min(current_interval * 2, max_interval)
                    logger.warning(
                        "Health check failed. Backing off to %.1fs",
                        current_interval,
                    )
                else:
                    if current_interval > base_interval:
                        logger.info(
                            "Health check recovered. Resetting interval to %.1fs", base_interval
                        )
                    current_interval = base_interval
                    if self._shared_engine:
                        await asyncio.to_thread(health.persist_snapshot, self._shared_engine, data)
            except Exception as e:  # noqa: BLE001
                current_interval = min(current_interval * 2, max_interval)
                logger.error(
                    "Health loop critical error: %s. Backing off to %.1fs", e, current_interval
                )

            try:
                await asyncio.sleep(current_interval)
            except asyncio.CancelledError:
                break
