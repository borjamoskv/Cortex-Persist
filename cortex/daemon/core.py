"""MoskvDaemon — Main daemon orchestrator."""

from __future__ import annotations

import json
import logging
import signal
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import httpx

from cortex.daemon.alerts import AlertHandlerMixin
from cortex.daemon.healing import HealingMixin
from cortex.daemon.models import (
    AGENT_DIR,
    CONFIG_FILE,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_COOLDOWN,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    STATUS_FILE,
    DaemonStatus,
)
from cortex.daemon.monitors import (
    AutonomousMejoraloMonitor,
    CertMonitor,
    CloudSyncMonitor,
    CompactionMonitor,
    DiskMonitor,
    EngineHealthCheck,
    EntropyMonitor,
    GhostWatcher,
    MemorySyncer,
    NeuralIntentMonitor,
    PerceptionMonitor,
    SecurityMonitor,
    SiteMonitor,
)
from cortex.daemon.sidecar.sentinel_monitor.monitor import SentinelMonitor
from cortex.daemon.sidecar.telemetry.fiat_oracle import FiatOracle

__all__ = ["MoskvDaemon"]

logger = logging.getLogger("moskv-daemon")

MAX_CONSECUTIVE_FAILURES = 3


class MoskvDaemon(AlertHandlerMixin, HealingMixin):
    """MOSKV-1 persistent watchdog.

    Orchestrates all monitors and sends alerts.
    Configuration is loaded from ~/.cortex/daemon_config.json when present.

    Usage:
        daemon = MoskvDaemon()
        daemon.check()           # Run once
        daemon.run(interval=300) # Run forever
    """

    def __init__(
        self,
        sites: list[str] | None = None,
        config_dir: Path = AGENT_DIR / "memory",
        stale_hours: float = DEFAULT_STALE_HOURS,
        memory_stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
        cooldown: float = DEFAULT_COOLDOWN,
        notify: bool = True,
    ):
        self.notify_enabled = notify
        self.config_dir = config_dir
        self._shutdown = False
        self._stop_event = threading.Event()
        self._failure_counts: dict[str, int] = {}
        self._healed_total: int = 0

        file_config = self._load_config()
        resolved_sites = sites or file_config.get("sites", [])

        self.site_monitor = SiteMonitor(resolved_sites)
        self.ghost_watcher = GhostWatcher(
            config_dir / "ghosts.json",
            file_config.get("stale_hours", stale_hours),
        )
        self.memory_syncer = MemorySyncer(
            config_dir / "system.json",
            file_config.get("memory_stale_hours", memory_stale_hours),
        )
        # Single shared engine instance to prevent memory leaks/pool exhaustion (HIGH-004)
        try:
            from cortex.engine import CortexEngine

            self._shared_engine = CortexEngine()
        except ImportError:
            self._shared_engine = None

        self.auto_mejoralo = AutonomousMejoraloMonitor(
            projects=file_config.get("auto_mejoralo_projects", {}),
            interval_seconds=file_config.get("auto_mejoralo_interval", 1800),
            engine=self._shared_engine,
        )
        self.entropy_monitor = EntropyMonitor(
            projects=file_config.get(
                "entropy_projects", file_config.get("auto_mejoralo_projects", {})
            ),
            interval_seconds=file_config.get("entropy_interval", 1800),
            threshold=90,
            engine=self._shared_engine,
        )
        self.compaction_monitor = CompactionMonitor(
            projects=list(file_config.get("auto_mejoralo_projects", {}).keys()),
            interval_seconds=file_config.get("compaction_interval", 28800),
            engine=self._shared_engine,
        )
        self.perception_monitor = PerceptionMonitor(
            workspace=file_config.get(
                "watch_path", str(Path.home() / "cortex")
            ),  # Defaulting to the workspace
            interval_seconds=file_config.get("perception_interval", 300),
            engine=self._shared_engine,
        )
        self.neural_monitor = NeuralIntentMonitor()
        self.security_monitor = SecurityMonitor(
            log_path=file_config.get("security_log_path", "~/.cortex/firewall.log"),
            threshold=file_config.get("security_threshold", 0.85),
        )

        try:
            from cortex.database.pool import CortexConnectionPool
            from cortex.daemon.sidecar.telemetry import ASTOracle
            from cortex.engine_async import AsyncCortexEngine

            db_path = file_config.get("db_path", str(CORTEX_DB))
            pool = CortexConnectionPool(db_path)
            self._async_engine = AsyncCortexEngine(pool=pool, db_path=db_path)
            self.ast_oracle = ASTOracle(
                engine=self._async_engine,
                watch_dir=Path(file_config.get("watch_path", str(CORTEX_DIR))),
            )
            self.fiat_oracle = FiatOracle(
                engine=self._shared_engine,
                interval=file_config.get("fiat_interval", 30.0),
            )
            self.sentinel_oracle = SentinelMonitor(
                check_interval=file_config.get("sentinel_interval", 60),
            )
        except ImportError:
            self._async_engine = None
            self.ast_oracle = None
            self.fiat_oracle = None
            self.sentinel_oracle = None

        cert_hostnames = [
            h.replace("https://", "").replace("http://", "").split("/")[0]
            for h in resolved_sites
            if h.startswith("https://")
        ]
        self.cert_monitor = CertMonitor(
            cert_hostnames,
            file_config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS),
        )
        self.engine_health = EngineHealthCheck(Path(file_config.get("db_path", str(CORTEX_DB))))
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )
        self.cloud_sync_monitor = CloudSyncMonitor(
            interval_seconds=file_config.get("cloud_sync_interval", 15),
            engine=self._shared_engine,
        )

        self._last_alerts: dict[str, float] = {}
        self._cooldown = file_config.get("cooldown", cooldown)

        # Time Tracker (for flushing heartbeats)
        try:
            from cortex.database.core import connect
            from cortex.timing import TimingTracker

            self.timing_conn = connect(
                file_config.get("db_path", str(CORTEX_DB)),
            )
            self.tracker = TimingTracker(self.timing_conn)
        except (ImportError, sqlite3.Error) as e:
            logger.error("Failed to init TimeTracker: %s", e)
            self.tracker = None

    @staticmethod
    def _load_config() -> dict:
        """Load daemon config from ~/.cortex/daemon_config.json if it exists."""
        if not CONFIG_FILE.exists():
            return {}
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load daemon config: %s", e)
            return {}

    def check(self) -> DaemonStatus:
        """Run all checks once. Returns DaemonStatus."""
        check_start = time.monotonic()
        now = datetime.now(timezone.utc).isoformat()
        status = DaemonStatus(checked_at=now)

        # Run all monitors through unified runner
        self._run_monitor(status, "sites", self.site_monitor, self._alert_sites, method="check_all")
        self._run_monitor(status, "stale_ghosts", self.ghost_watcher, self._alert_ghosts)
        self._run_monitor(status, "memory_alerts", self.memory_syncer, self._alert_memory)
        self._run_monitor(status, "cert_alerts", self.cert_monitor, self._alert_certs)
        self._run_monitor(status, "engine_alerts", self.engine_health, self._alert_engine)
        self._run_monitor(status, "disk_alerts", self.disk_monitor, self._alert_disk)
        self._run_monitor(status, "mejoralo_alerts", self.auto_mejoralo, self._alert_mejoralo)
        self._run_monitor(status, "entropy_alerts", self.entropy_monitor, self._alert_entropy)
        self._run_monitor(
            status, "compaction_alerts", self.compaction_monitor, self._alert_compaction
        )
        self._run_monitor(
            status, "perception_alerts", self.perception_monitor, self._alert_perception
        )
        self._run_monitor(status, "security_alerts", self.security_monitor, self._alert_security)
        self._run_monitor(
            status,
            "cloud_sync_alerts",
            self.cloud_sync_monitor,
            self._alert_cloud_sync,
        )

        self._auto_sync(status)
        self._flush_timer()

        status.check_duration_ms = (time.monotonic() - check_start) * 1000
        self._save_status(status)

        level = "✅" if status.all_healthy else "⚠️"
        logger.info(
            "%s Check complete in %.0fms: %d sites, %d stale ghosts, %d memory alerts",
            level,
            status.check_duration_ms,
            len(status.sites),
            len(status.stale_ghosts),
            len(status.memory_alerts),
        )
        return status

    def _run_monitor(
        self,
        status: DaemonStatus,
        attr: str,
        monitor: object,
        alert_fn: Callable,
        method: str = "check",
    ) -> None:
        """Run a single monitor, store results, and fire alerts."""
        monitor_name = type(monitor).__name__
        try:
            results = getattr(monitor, method)()
            if isinstance(results, list):
                setattr(status, attr, results)
            alert_fn(results)
            # Reset failure counter on success
            self._failure_counts.pop(monitor_name, None)
        except (httpx.HTTPError, OSError, ValueError, sqlite3.Error, RuntimeError, TypeError) as e:
            status.errors.append(f"{monitor_name} error: {e}")
            logger.exception("%s failed", monitor_name)
            count = self._failure_counts.get(monitor_name, 0) + 1
            self._failure_counts[monitor_name] = count
            if count >= MAX_CONSECUTIVE_FAILURES:
                self._heal_monitor(attr, monitor_name)
                self._failure_counts.pop(monitor_name, None)

    #   _alert_sites, _alert_ghosts, _alert_memory, _alert_certs,
    #   _alert_engine, _alert_disk, _alert_mejoralo, _alert_entropy,
    #   _dispatch_warm_repair, _alert_perception, _alert_neural, _alert_compaction

    def _alert_compaction(self, alerts: list) -> None:
        """Handler para CompactionAlert."""
        if not alerts:
            return
        for a in alerts:
            key = f"compaction:{a.project}"
            if self._should_alert(key):
                self._terminal_notify("Compaction completed", a.message)
                self._last_alerts[key] = time.monotonic()

    def _alert_cloud_sync(self, alerts: list) -> None:
        """Handler for CloudSyncAlert."""
        if not alerts:
            return
        for a in alerts:
            logger.debug(a.message)
            logger.info("🧠 CORTEX Sleep Cycle: %s", a.message)

    def _flush_timer(self) -> None:
        """Flush accumulated time tracker heartbeats."""
        if not self.tracker:
            return
        try:
            entries = self.tracker.flush()
            if entries > 0:
                logger.info("TimeTracker: Consolidado %d entradas de tiempo.", entries)
        except sqlite3.Error as e:
            logger.error("TimeTracker flush error: %s", e)

    def _auto_sync(self, status: DaemonStatus) -> None:
        """Automatic memory JSON ↔ CORTEX DB synchronization."""
        if not self._shared_engine:
            return
        try:
            from cortex.sync import export_snapshot, export_to_json, sync_memory

            sync_result = sync_memory(self._shared_engine)
            if sync_result.had_changes:
                logger.info("Sync automático: %d hechos sincronizados", sync_result.total)
            wb_result = export_to_json(self._shared_engine)
            if wb_result.had_changes:
                logger.info(
                    "Write-back automático: %d archivos, %d items",
                    wb_result.files_written,
                    wb_result.items_exported,
                )
            import asyncio

            asyncio.run(export_snapshot(self._shared_engine))

        except (sqlite3.Error, OSError, ValueError) as e:
            status.errors.append(f"Memory sync error: {e}")
            logger.exception("Memory sync failed")

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run checks in a loop until stopped."""

        def _handle_signal(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            self._shutdown = True
            self._stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("🚀 MOSKV-1 Daemon starting (interval=%ds)", interval)

        # Start fast-polling low-latency loop for Neural Sync
        neural_thread = threading.Thread(
            target=self._run_neural_loop, name="NeuralSync", daemon=True
        )
        neural_thread.start()
        self._threads.append(neural_thread)

        if self.ast_oracle:
            t = threading.Thread(target=self._run_ast_oracle_loop, name="ASTOracle", daemon=True)
            t.start()
            self._threads.append(t)

        if self.fiat_oracle:
            t = threading.Thread(
                target=self.fiat_oracle.run_sync_loop, name="FiatOracle", daemon=True
            )
            t.start()
            self._threads.append(t)

        if getattr(self, "sentinel_oracle", None):
            t = threading.Thread(
                target=self._run_sentinel_oracle_loop,
                name="SentinelOracle",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

        logger.info("Daemon started with %d threads", len(self._threads))

        try:
            while not self._shutdown:
                self.check()
                self._stop_event.wait(timeout=interval)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("MOSKV-1 Daemon stopped")

    def _run_neural_loop(self) -> None:
        """Fast polling loop for zero-latency neural intent ingestion."""
        logger.info("🧠 Neural-Bandwidth Sync thread started (1Hz)")
        while not self._shutdown:
            try:
                alerts = self.neural_monitor.check()
                if alerts:
                    self._alert_neural(alerts)
            except (ValueError, OSError, RuntimeError) as e:
                logger.debug("Neural loop error: %s", e)
            self._stop_event.wait(timeout=1.0)

    def _run_ast_oracle_loop(self) -> None:
        """Runs the AST Oracle event loop for live AST mutation interception."""
        import asyncio

        logger.info("👁️ AST Oracle thread started (FSEvents)")

        async def _lifecycle():
            # Run the observer until shutdown is flagged
            task = asyncio.create_task(self.ast_oracle.start())
            while not self._shutdown:
                await asyncio.sleep(1.0)
            await self.ast_oracle.stop()
            await task

        try:
            asyncio.run(_lifecycle())
        except Exception as e:
            logger.error("AST Oracle loop error: %s", e)

    def _run_sentinel_oracle_loop(self) -> None:
        """Runs the Sentinel Oracle polling loop."""
        import asyncio

        logger.info("🛡️ CORTEX Sentinel Oracle thread started")
        try:
            # We are running this in a new thread, so asyncio.run is perfect.
            asyncio.run(self.sentinel_oracle.run_loop())
        except Exception as e:
            logger.error("Sentinel Oracle loop error: %s", e)

    def _should_alert(self, key: str) -> bool:
        """Rate-limit duplicate alerts (1 per hour per key)."""
        if not self.notify_enabled:
            return False
        now = time.monotonic()
        last = self._last_alerts.get(key, 0)
        if now - last < self._cooldown:
            return False
        self._last_alerts[key] = now
        return True

    def _save_status(self, status: DaemonStatus) -> None:
        """Persist status to daemon_status.json."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))
        except OSError as e:
            logger.error("Failed to save status: %s", e)

    @staticmethod
    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
