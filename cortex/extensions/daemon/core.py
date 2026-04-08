"""MoskvDaemon — Main daemon orchestrator.

v2.0: Sovereign Async Loop — single event loop replaces N threads.
New subsystems: SovereignScheduler, HotStateDB, WatchdogHub, HumanCallbackAPI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from cortex.extensions.daemon.alerts import AlertHandlerMixin
from cortex.extensions.daemon.bootstrap_mixin import DaemonBootstrapMixin
from cortex.extensions.daemon.healing import HealingMixin
from cortex.extensions.daemon.loops_mixin import LoopsMixin
from cortex.extensions.daemon.models import (
    AGENT_DIR,
    CONFIG_FILE,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_COOLDOWN,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    STATUS_FILE,
    DaemonStatus,
)
from cortex.extensions.daemon.monitors import (
    CertMonitor,
    CompactionMonitor,
    EpistemicMonitor,
    EvaluationMonitor,
    GhostWatcher,
    MemorySyncer,
    NeuralIntentMonitor,
    PerceptionMonitor,
    SecurityMonitor,
    SignalMonitor,
    SiteMonitor,
    TombstoneMonitor,
    UnifiedMejoraloMonitor,
    WorkflowMonitor,
)
from cortex.extensions.daemon.sidecar.sentinel_monitor.monitor import SentinelMonitor
from cortex.extensions.daemon.sidecar.telemetry.fiat_oracle import FiatOracle
from cortex.utils.time import utc_now

# ─── Sovereign Async Subsystems (v2.0) ─────────────────────────────────
try:
    from cortex.extensions.daemon.sidecar.telemetry.iot_oracle import IoTOracle

    _IOT_ORACLE_AVAILABLE = True
except ImportError:
    _IOT_ORACLE_AVAILABLE = False


__all__ = ["MoskvDaemon"]

logger = logging.getLogger("moskv-daemon")

MAX_CONSECUTIVE_FAILURES = 3


class MoskvDaemon(DaemonBootstrapMixin, AlertHandlerMixin, HealingMixin, LoopsMixin):
    """MOSKV-1 persistent watchdog. Orchestrates monitors and sends alerts."""

    def __init__(
        self,
        sites: Optional[list[str]] = None,
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
        self._threads: list[threading.Thread] = []

        file_config = self._load_config()
        self._cooldown = file_config.get("cooldown", cooldown)
        self._last_alerts: dict[str, float] = {}

        self._init_core_monitors(file_config, sites, stale_hours, memory_stale_hours)
        self._init_advanced_monitors(file_config)
        self._init_external_oracles(file_config, resolved_sites=[])  # sites used in certs
        self._init_background_agents(file_config)
        self._init_autopoiesis(file_config)
        self._init_sovereign_subsystems(file_config)
        self._init_persistence_checkers(file_config)

    def _init_core_monitors(
        self,
        file_config: dict,
        sites: Optional[list[str]],
        stale_hours: float,
        memory_stale_hours: float,
    ) -> None:
        """Initialize basic status monitors."""
        resolved_sites = sites or file_config.get("sites", [])
        self.site_monitor = SiteMonitor(resolved_sites)
        self.ghost_watcher = GhostWatcher(
            self.config_dir / "ghosts.json",
            file_config.get("stale_hours", stale_hours),
        )
        self.memory_syncer = MemorySyncer(
            self.config_dir / "system.json",
            file_config.get("memory_stale_hours", memory_stale_hours),
        )
        self.evaluation_monitor = EvaluationMonitor(db_path=CORTEX_DB)
        # Shared engine
        try:
            from cortex.engine import CortexEngine

            self._shared_engine = CortexEngine()
        except ImportError:
            self._shared_engine = None

    def _init_advanced_monitors(self, file_config: dict) -> None:
        """Initialize optimization and analysis monitors."""
        self.mejoralo_monitor = UnifiedMejoraloMonitor(
            projects=file_config.get("auto_mejoralo_projects", {}),
            interval_seconds=file_config.get("auto_mejoralo_interval", 1800),
            threshold=90,
            engine=self._shared_engine,
            auto_heal=True,
        )
        self.compaction_monitor = CompactionMonitor(
            projects=list(file_config.get("auto_mejoralo_projects", {}).keys()),
            interval_seconds=file_config.get("compaction_interval", 28800),
            engine=self._shared_engine,
        )
        self.perception_monitor = PerceptionMonitor(
            workspace=file_config.get("watch_path", str(Path.home() / "cortex")),
            interval_seconds=file_config.get("perception_interval", 300),
            engine=self._shared_engine,
        )
        self.neural_monitor = NeuralIntentMonitor()
        self.security_monitor = SecurityMonitor(
            log_path=file_config.get("security_log_path", "~/.cortex/firewall.log"),
            threshold=file_config.get("security_threshold", 0.85),
        )
        self.workflow_monitor = WorkflowMonitor(
            ghosts_path=self.config_dir / "ghosts.json",
            memory_path=self.config_dir / "system.json",
            db_path=Path(file_config.get("db_path", str(CORTEX_DB))),
        )
        self.epistemic_monitor = EpistemicMonitor(
            engine=self._shared_engine,
            eval_interval_seconds=file_config.get("epistemic_eval_interval", 600),
            critical_repair_threshold=file_config.get("epistemic_repair_threshold", 5),
            decay_velocity_threshold=file_config.get("epistemic_decay_threshold", -0.05),
            stale_ratio_threshold=file_config.get("epistemic_stale_ratio", 0.20),
        )

    def _init_external_oracles(self, file_config: dict, resolved_sites: list[str]) -> None:
        """Initialize oracles and external connectivity monitors."""
        self.signal_monitor = SignalMonitor(
            db_path=file_config.get("db_path", str(CORTEX_DB)),
            engine=self._shared_engine,
        )
        self.tombstone_monitor = TombstoneMonitor(
            db_path=file_config.get("db_path", str(CORTEX_DB))
        )

        try:
            from cortex.database.pool import CortexConnectionPool
            from cortex.engine import CortexEngine as AsyncCortexEngine
            from cortex.extensions.daemon.sidecar.telemetry import ASTOracle

            db_path = file_config.get("db_path", str(CORTEX_DB))
            pool = CortexConnectionPool(db_path)
            self._async_engine = AsyncCortexEngine(pool=pool, db_path=db_path)
            self.ast_oracle = ASTOracle(
                engine=self._async_engine,
                watch_dir=Path(file_config.get("watch_path", str(CORTEX_DIR))),
            )
            if _IOT_ORACLE_AVAILABLE:
                self.iot_oracle = IoTOracle(
                    engine=self._async_engine,
                    poll_interval=float(file_config.get("iot_interval", 10.0)),
                    enable_simulated_sensors=file_config.get("iot_simulated", True),
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
        now = utc_now().isoformat()
        status = DaemonStatus(checked_at=now)
        self._run_monitor(status, "sites", self.site_monitor, self._alert_sites, method="check_all")
        self._run_monitor(status, "stale_ghosts", self.ghost_watcher, self._alert_ghosts)
        self._run_monitor(status, "memory_alerts", self.memory_syncer, self._alert_memory)
        self._run_monitor(status, "cert_alerts", self.cert_monitor, self._alert_certs)
        self._run_monitor(status, "engine_alerts", self.engine_health, self._alert_engine)
        self._run_monitor(status, "disk_alerts", self.disk_monitor, self._alert_disk)
        self._run_monitor(
            status, "evaluation_alerts", self.evaluation_monitor, self._alert_evaluation
        )
        self._run_monitor(status, "mejoralo_alerts", self.mejoralo_monitor, self._alert_mejoralo)
        self._run_monitor(
            status, "compaction_alerts", self.compaction_monitor, self._alert_compaction
        )
        self._run_monitor(
            status, "perception_alerts", self.perception_monitor, self._alert_perception
        )
        self._run_monitor(status, "security_alerts", self.security_monitor, self._alert_security)
        self._run_monitor(status, "signal_alerts", self.signal_monitor, self._alert_signals)
        self._run_monitor(
            status, "cloud_sync_alerts", self.cloud_sync_monitor, self._alert_cloud_sync
        )
        self._run_monitor(status, "tombstone_alerts", self.tombstone_monitor, self._alert_tombstone)
        self._run_monitor(status, "workflow_alerts", self.workflow_monitor, self._alert_workflows)
        self._run_monitor(status, "epistemic_alerts", self.epistemic_monitor, self._alert_workflows)
        if self.aether_monitor is not None:
            self._run_monitor(status, "aether_alerts", self.aether_monitor, self._alert_aether)
            if hasattr(self, "auto_immune_monitor"):
                self._run_monitor(
                    status, "auto_immune_alerts", self.auto_immune_monitor, self._alert_auto_immune
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
            if asyncio.iscoroutine(results):
                results = asyncio.run(results)

            if isinstance(results, list):
                setattr(status, attr, results)
            alert_fn(results)
            self._failure_counts.pop(monitor_name, None)
        except Exception as e:  # noqa: BLE001
            status.errors.append(f"{monitor_name} error: {e}")
            logger.exception("%s failed", monitor_name)
            count = self._failure_counts.get(monitor_name, 0) + 1
            self._failure_counts[monitor_name] = count
            if count >= MAX_CONSECUTIVE_FAILURES:
                self._heal_monitor(attr, monitor_name)
                self._failure_counts.pop(monitor_name, None)

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run the daemon. Uses sovereign async loop if available, else legacy threads."""
        from cortex.events.loop import sovereign_run

        try:
            sovereign_run(self.run_sovereign(interval=interval))
        except ImportError:
            logger.info("uvloop not available, falling back to legacy threading mode")
            self._run_legacy(interval=interval)

    async def run_sovereign(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Sovereign async execution — single event loop, all subsystems as tasks.

        This is the x100 upgrade: replaces N threads with N async tasks on one loop.
        All subsystems share the same DistributedEventBus and HotStateDB.
        """
        loop = asyncio.get_running_loop()

        # Signal handling (works in main thread only)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._signal_shutdown)
            except (NotImplementedError, RuntimeError):
                pass  # Windows or non-main thread

        logger.info("🚀 MOSKV-1 Sovereign Daemon starting (interval=%ds)", interval)

        # Track uptime in hot state
        if self.hot_state is not None:
            self.hot_state.set("daemon.mode", "sovereign")
            self.hot_state.set("daemon.started_at", utc_now().isoformat())

        # ─── Spawn all subsystems as async tasks ──────────────────
        tasks: list[asyncio.Task] = []

        # Core check loop (replaces the main while loop)
        tasks.append(asyncio.create_task(
            self._sovereign_check_loop(interval), name="CheckLoop"
        ))

        # Scheduler
        if self.scheduler is not None:
            self._register_default_schedules()
            tasks.append(asyncio.create_task(
                self.scheduler.run(), name="Scheduler"
            ))

        # WatchdogHub
        if self.watchdog_hub is not None:
            tasks.append(asyncio.create_task(
                self.watchdog_hub.start(), name="WatchdogHub"
            ))

        # Human Callback API
        if self.callback_api is not None:
            tasks.append(asyncio.create_task(
                self.callback_api.serve(), name="CallbackAPI"
            ))

        # Legacy thread-based subsystems that need their own asyncio.run()
        # These are spawned as threads because they have blocking I/O
        if self._aether_daemon is not None:
            self._spawn_thread(self._aether_daemon.start, "AetherAgent")
        if self.fiat_oracle:
            self._spawn_thread(self.fiat_oracle.run_sync_loop, "FiatOracle")

        # Pure async subsystems
        self._spawn_thread(self._run_neural_loop, "NeuralSync")
        if self.ast_oracle:
            self._spawn_thread(self._run_ast_oracle_loop, "ASTOracle")
        if getattr(self, "iot_oracle", None):
            self._spawn_thread(self._run_iot_oracle_loop, "IoTOracle")
        if self.heartbeat_daemon:
            self._spawn_thread(self._run_heartbeat_loop, "HeartbeatDaemon")
        if self.entropic_wake_daemon:
            self._spawn_thread(self._run_entropic_wake_loop, "EntropicWakeDaemon")
        if self.frontier_daemon:
            self._spawn_thread(self._run_frontier_loop, "FrontierDaemon")
        if getattr(self, "zero_prompting_daemon", None):
            self._spawn_thread(self._run_zero_prompting_loop, "ZeroPromptingDaemon")
        if getattr(self, "epistemic_breaker_daemon", None):
            self._spawn_thread(self._run_epistemic_breaker_loop, "EpistemicBreakerDaemon")
        if getattr(self, "sentinel_oracle", None):
            self._spawn_thread(self._run_sentinel_oracle_loop, "SentinelOracle")
        self._spawn_thread(self._run_health_loop, "HealthMonitor")

        async_count = len(tasks)
        thread_count = len(self._threads)
        logger.info(
            "Sovereign Daemon started: %d async tasks + %d legacy threads",
            async_count,
            thread_count,
        )

        try:
            # Wait until shutdown signal
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            await self._sovereign_shutdown()

    async def _sovereign_check_loop(self, interval: int) -> None:
        """Async version of the main check loop."""
        while not self._shutdown:
            try:
                # Run check in thread pool to not block the event loop
                await asyncio.to_thread(self.check)

                # Update hot state cycle counter
                if self.hot_state is not None:
                    self.hot_state.increment("cycle_count")

            except Exception as e:  # noqa: BLE001
                logger.error("Check loop error: %s", e)

            # Async sleep instead of threading.Event.wait
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def _sovereign_shutdown(self) -> None:
        """Graceful shutdown of all sovereign subsystems."""
        logger.info("Sovereign shutdown initiated...")

        if self.watchdog_hub is not None:
            await self.watchdog_hub.stop()
        if self.scheduler is not None:
            await self.scheduler.stop()
        if self._event_bus is not None:
            await self._event_bus.shutdown()
        if self.entropic_wake_daemon:
            self.entropic_wake_daemon.stop()
        if self.frontier_daemon:
            self.frontier_daemon.stop()
        if getattr(self, "zero_prompting_daemon", None):
            self.zero_prompting_daemon.stop()  # type: ignore[union-attr]
        if getattr(self, "epistemic_breaker_daemon", None):
            self.epistemic_breaker_daemon.stop()  # type: ignore[union-attr]

        # Persist final state
        if self.hot_state is not None:
            self.hot_state.set("daemon.stopped_at", utc_now().isoformat())

        logger.info("MOSKV-1 Sovereign Daemon stopped")

    def _signal_shutdown(self) -> None:
        """Signal handler for async loop."""
        logger.info("Received shutdown signal")
        self._shutdown = True
        self._stop_event.set()
        # Cancel all running tasks
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()

    def _register_default_schedules(self) -> None:
        """Register built-in recurring tasks with the scheduler."""
        if self.scheduler is None:
            return

        # Hot state TTL purge every 10 minutes
        if self.hot_state is not None:
            self.scheduler.add_recurring(
                "purge_expired_state",
                lambda: asyncio.coroutine(lambda: self.hot_state.purge_expired())(),  # type: ignore
                interval_s=600,
                priority=8,
            )

    def _run_legacy(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Legacy threading-based execution (fallback)."""
        def _handle_signal(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            self._shutdown = True
            self._stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("🚀 MOSKV-1 Daemon starting [LEGACY] (interval=%ds)", interval)

        if self._aether_daemon is not None:
            self._spawn_thread(self._aether_daemon.start, "AetherAgent")
        self._spawn_thread(self._run_neural_loop, "NeuralSync")
        if self.ast_oracle:
            self._spawn_thread(self._run_ast_oracle_loop, "ASTOracle")
        if getattr(self, "iot_oracle", None):
            self._spawn_thread(self._run_iot_oracle_loop, "IoTOracle")
        if self.fiat_oracle:
            self._spawn_thread(self.fiat_oracle.run_sync_loop, "FiatOracle")
        if self.heartbeat_daemon:
            self._spawn_thread(self._run_heartbeat_loop, "HeartbeatDaemon")
        if self.entropic_wake_daemon:
            self._spawn_thread(self._run_entropic_wake_loop, "EntropicWakeDaemon")
        if self.frontier_daemon:
            self._spawn_thread(self._run_frontier_loop, "FrontierDaemon")
        if getattr(self, "zero_prompting_daemon", None):
            self._spawn_thread(self._run_zero_prompting_loop, "ZeroPromptingDaemon")
        if getattr(self, "epistemic_breaker_daemon", None):
            self._spawn_thread(self._run_epistemic_breaker_loop, "EpistemicBreakerDaemon")
        if getattr(self, "sentinel_oracle", None):
            self._spawn_thread(self._run_sentinel_oracle_loop, "SentinelOracle")
        self._spawn_thread(self._run_health_loop, "HealthMonitor")

        logger.info("Daemon started with %d threads", len(self._threads))

        try:
            while not self._shutdown:
                self.check()
                self._stop_event.wait(timeout=interval)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("MOSKV-1 Daemon stopped")
            if self.entropic_wake_daemon:
                self.entropic_wake_daemon.stop()
            if self.frontier_daemon:
                self.frontier_daemon.stop()
            if getattr(self, "zero_prompting_daemon", None):
                self.zero_prompting_daemon.stop()  # type: ignore[union-attr]
            if getattr(self, "epistemic_breaker_daemon", None):
                self.epistemic_breaker_daemon.stop()  # type: ignore[union-attr]

    def _save_status(self, status: DaemonStatus) -> None:
        """Persist status to disk."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))
        except OSError as e:
            logger.error("Failed to save status: %s", e)

    @staticmethod
    def load_status() -> Optional[dict]:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
