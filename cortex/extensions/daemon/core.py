from typing import Any
from collections.abc import Callable

"""MoskvDaemon - Main daemon orchestrator.

v2.0: Sovereign Async Loop - single event loop replaces N threads.
New subsystems: SovereignScheduler, HotStateDB, WatchdogHub, HumanCallbackAPI.
"""

import asyncio
import json
import logging
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from cortex.extensions.daemon.alerts import AlertHandlerMixin
from cortex.extensions.daemon.core_support import (
    init_advanced_monitors,
    init_background_agents,
    init_core_monitors,
    init_external_oracles,
)
from cortex.extensions.daemon.healing import HealingMixin
from cortex.extensions.daemon.loops_mixin import LoopsMixin
from cortex.extensions.daemon.models import (
    AGENT_DIR,
    DEFAULT_COOLDOWN,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    STATUS_FILE,
    DaemonStatus,
    CORTEX_DB,
    CORTEX_DIR,
)

from cortex.extensions.daemon.monitors import (
    CloudSyncMonitor,
    DiskMonitor,
    EngineHealthCheck,
)

try:
    from cortex.extensions.daemon.hot_state import HotStateDB
    _HOT_STATE_AVAILABLE = True
except ImportError:
    _HOT_STATE_AVAILABLE = False

try:
    from cortex.extensions.daemon.scheduler import SovereignScheduler
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _SCHEDULER_AVAILABLE = False

try:
    from cortex.extensions.daemon.watchers import WatchdogHub
    _WATCHDOG_HUB_AVAILABLE = True
except ImportError:
    _WATCHDOG_HUB_AVAILABLE = False

try:
    from cortex.extensions.daemon.api import HumanCallbackAPI  # pyright: ignore[reportMissingImports]
    _API_AVAILABLE = True
except ImportError:
    _API_AVAILABLE = False

try:
    from cortex.extensions.daemon.centaur.heartbeat import HeartbeatDaemon
    from cortex.extensions.daemon.centaur.entropic_queue import EntropicQueue  # pyright: ignore[reportMissingImports]
    from cortex.extensions.daemon.centaur.engine import CentauroEngine  # pyright: ignore[reportMissingImports]
    _CENTAUR_AVAILABLE = True
except ImportError:
    _CENTAUR_AVAILABLE = False

try:
    from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon
    _ENTROPIC_WAKE_AVAILABLE = True
except ImportError:
    _ENTROPIC_WAKE_AVAILABLE = False

try:
    from cortex.extensions.daemon.frontier import FrontierDaemon
    _FRONTIER_AVAILABLE = True
except ImportError:
    _FRONTIER_AVAILABLE = False

try:
    from cortex.extensions.daemon.zero_prompting import ZeroPromptingDaemon
    _ZERO_PROMPTING_AVAILABLE = True
except ImportError:
    _ZERO_PROMPTING_AVAILABLE = False

try:
    from cortex.extensions.daemon.epistemic_breaker import EpistemicBreakerDaemon
    _EPISTEMIC_BREAKER_AVAILABLE = True
except ImportError:
    _EPISTEMIC_BREAKER_AVAILABLE = False
__all__ = ["MoskvDaemon"]
logger = logging.getLogger("moskv-daemon")
MAX_CONSECUTIVE_FAILURES = 3

from cortex.extensions.daemon.resource_mgr import ResourceMgrMixin
from cortex.extensions.daemon.event_loop import EventLoopMixin

class MoskvDaemon(AlertHandlerMixin, HealingMixin, LoopsMixin, ResourceMgrMixin, EventLoopMixin):
    """MOSKV-1 persistent watchdog. Orchestrates monitors and sends alerts."""

    tracker: Any
    site_monitor: Any
    ghost_watcher: Any
    memory_syncer: Any
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
    mejoralo_monitor: Any
    _healed_total: int
    _failure_counts: dict[str, int]
    _shutdown: bool
    _stop_event: threading.Event
    _threads: list[threading.Thread]
    _async_engine: Any
    hot_state: Any
    _event_bus: Any
    config_dir: Path

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
        self._threads: list[threading.Thread] = []
        file_config = self._load_config()
        self._cooldown = file_config.get("cooldown", cooldown)
        self._last_alerts: dict[str, float] = {}
        init_core_monitors(self, file_config, sites, stale_hours, memory_stale_hours)
        init_advanced_monitors(self, file_config)
        init_external_oracles(self, file_config, resolved_sites=[])
        init_background_agents(self, file_config)
        self._init_autopoiesis(file_config)
        self._init_sovereign_subsystems(file_config)
        self._init_persistence_checkers(file_config)

    

    

    

    def check(self) -> DaemonStatus:
        """Run all checks once. Returns DaemonStatus."""
        check_start = time.monotonic()
        now = datetime.fromtimestamp(time.monotonic(), tz=timezone.utc).isoformat()
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
                    status, "auto_immune_alerts", self.auto_immune_monitor, self._alert_auto_immune  # pyright: ignore[reportAttributeAccessIssue]
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

    

    async def run_sovereign(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Sovereign async execution - single event loop, all subsystems as tasks.

        This is the x100 upgrade: replaces N threads with N async tasks on one loop.
        All subsystems share the same DistributedEventBus and HotStateDB.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._signal_shutdown)
            except (NotImplementedError, RuntimeError):
                import logging
                logging.getLogger(__name__).error('DETECTIVE-OMEGA: Silent exception swallowed in core.py')
        logger.info("🚀 MOSKV-1 Sovereign Daemon starting (interval=%ds)", interval)
        if self.hot_state is not None:
            self.hot_state.set("daemon.mode", "sovereign")
            self.hot_state.set(
                "daemon.started_at",
                datetime.fromtimestamp(time.monotonic(), tz=timezone.utc).isoformat(),
            )
        tasks: list[asyncio.Task] = []
        tasks.append(asyncio.create_task(self._sovereign_check_loop(interval), name="CheckLoop"))
        if self.scheduler is not None:
            self._register_default_schedules()
            tasks.append(asyncio.create_task(self.scheduler.run(), name="Scheduler"))
        if self.watchdog_hub is not None:
            tasks.append(asyncio.create_task(self.watchdog_hub.start(), name="WatchdogHub"))
        if self.callback_api is not None:
            tasks.append(asyncio.create_task(self.callback_api.serve(), name="CallbackAPI"))
        if self._aether_daemon is not None:
            tasks.append(
                asyncio.create_task(
                    asyncio.to_thread(self._aether_daemon.start), name="AetherAgent"
                )
            )
        if self.fiat_oracle:
            tasks.append(asyncio.create_task(self.fiat_oracle.run_loop(), name="FiatOracle"))
        tasks.append(asyncio.create_task(self._run_neural_loop_async(), name="NeuralSync"))
        if self.ast_oracle:
            tasks.append(asyncio.create_task(self._run_lifecycle_daemon_async(self.ast_oracle, "AST Oracle", "👁️"), name="ASTOracle"))
        if getattr(self, "iot_oracle", None):
            tasks.append(asyncio.create_task(self._run_lifecycle_daemon_async(self.iot_oracle, "IoT Oracle", "📡"), name="IoTOracle"))
        if self.heartbeat_daemon:
            tasks.append(
                asyncio.create_task(self._run_lifecycle_daemon_async(self.heartbeat_daemon, "Heartbeat", "❤️"), name="HeartbeatDaemon")
            )
        if self.entropic_wake_daemon:
            tasks.append(
                asyncio.create_task(self._run_loop_daemon_async(self.entropic_wake_daemon, "Entropic Wake", "🌌"), name="EntropicWakeDaemon")
            )
        if self.frontier_daemon:
            tasks.append(
                asyncio.create_task(self._run_loop_daemon_async(self.frontier_daemon, "Frontier", "🚀"), name="FrontierDaemon")
            )
        if getattr(self, "zero_prompting_daemon", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.zero_prompting_daemon, "Zero-Prompting", "🧠"), name="ZeroPromptingDaemon"
                )
            )
        if getattr(self, "epistemic_breaker_daemon", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.epistemic_breaker_daemon, "Epistemic Breaker", "🛡️", run_method="run"), name="EpistemicBreakerDaemon"
                )
            )
        if getattr(self, "sentinel_oracle", None):
            tasks.append(
                asyncio.create_task(self._run_loop_daemon_async(self.sentinel_oracle, "Sentinel Oracle", "🛡️"), name="SentinelOracle")
            )
        tasks.append(asyncio.create_task(self._run_health_loop_async(), name="HealthMonitor"))
        async_count = len(tasks)
        thread_count = len(self._threads)
        logger.info(
            "Sovereign Daemon started: %d async tasks + %d legacy threads",
            async_count,
            thread_count,
        )
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            import logging
            logging.getLogger(__name__).error('DETECTIVE-OMEGA: Silent exception swallowed in core.py')
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
        if hasattr(self, "_event_bus") and self._event_bus is not None:
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
            self.hot_state.set("daemon.stopped_at", datetime.now(timezone.utc).isoformat())

        logger.info("MOSKV-1 Sovereign Daemon stopped")

    @staticmethod
    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None

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

    

    

    def _save_status(self, status: DaemonStatus) -> None:
        """Persist status to disk."""

        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

            STATUS_FILE.write_text(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))

        except OSError as e:
            logger.error("Failed to save status: %s", e)
