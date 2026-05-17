"""MoskvDaemon — Main daemon orchestrator.

v2.0: Sovereign Async Loop — single event loop replaces N threads.
New subsystems: SovereignScheduler, HotStateDB, WatchdogHub, HumanCallbackAPI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
    CONFIG_FILE,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_COOLDOWN,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    STATUS_FILE,
    DaemonStatus,
)
from cortex.extensions.daemon.monitors import (
    CloudSyncMonitor,
    DiskMonitor,
    EngineHealthCheck,
)

# ─── Sovereign Async Subsystems (v2.0) ─────────────────────────────────
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
    from cortex.extensions.daemon.api import HumanCallbackAPI

    _API_AVAILABLE = True
except ImportError:
    _API_AVAILABLE = False

try:
    from cortex.extensions.daemon.centaur.heartbeat import HeartbeatDaemon
    from cortex.extensions.daemon.centaur.queue import EntropicQueue
    from cortex.extensions.swarm.centauro_engine import CentauroEngine

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


class MoskvDaemon(AlertHandlerMixin, HealingMixin, LoopsMixin):
    """MOSKV-1 persistent watchdog. Orchestrates monitors and sends alerts."""

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
        init_external_oracles(self, file_config, resolved_sites=[])  # sites used in certs
        init_background_agents(self, file_config)
        self._init_autopoiesis(file_config)
        self._init_sovereign_subsystems(file_config)
        self._init_persistence_checkers(file_config)

    def _init_autopoiesis(self, file_config: dict) -> None:
        """Initialize Heartbeat and metabolism engines."""
        self.heartbeat_daemon = None
        if _CENTAUR_AVAILABLE:
            try:
                db_path = file_config.get("db_path", str(CORTEX_DB))
                centaur_queue = EntropicQueue(db_path=Path(db_path).parent / "entropic_queue.db")
                centauro_engine = CentauroEngine()
                self.heartbeat_daemon = HeartbeatDaemon(
                    queue=centaur_queue,
                    engine=centauro_engine,
                    poll_interval=float(file_config.get("heartbeat_interval", 30.0)),
                )
                logger.info("❤️  HeartbeatDaemon (Continuous Autopoiesis) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init HeartbeatDaemon: %s", e)

        self.frontier_daemon = None
        if _FRONTIER_AVAILABLE:
            try:
                self.frontier_daemon = FrontierDaemon(
                    engine=self._shared_engine,
                    metabolism_interval_hours=float(
                        file_config.get("frontier_metabolism_interval_hours", 12.0)
                    ),
                    ingestion_interval_hours=float(
                        file_config.get("frontier_ingestion_interval_hours", 24.0)
                    ),
                    allow_commits=file_config.get("frontier_allow_commits", True),
                )
                logger.info("🚀 Frontier Daemon (Evolution Engine) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Frontier Daemon: %s", e)

        self.zero_prompting_daemon = None
        if _ZERO_PROMPTING_AVAILABLE:
            try:
                self.zero_prompting_daemon = ZeroPromptingDaemon(
                    engine=self._shared_engine,
                    workspace_root=Path(file_config.get("watch_path", str(CORTEX_DIR))),
                    cycle_interval_hours=float(
                        file_config.get("zero_prompting_interval_hours", 24.0)
                    ),
                )
                logger.info("🧠 Zero-Prompting Evolution Daemon (Axioma Ω₇) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Zero-Prompting Daemon: %s", e)

        self.epistemic_breaker_daemon = None
        if _EPISTEMIC_BREAKER_AVAILABLE:
            try:
                self.epistemic_breaker_daemon = EpistemicBreakerDaemon(
                    engine=self._shared_engine,
                    check_interval_seconds=int(
                        file_config.get("epistemic_breaker_interval_seconds", 300)
                    ),
                    max_entropy_threshold=float(
                        file_config.get("epistemic_breaker_max_entropy", 0.85)
                    ),
                )
                logger.info("🛡️ Sovereign Epistemic Circuit Breaker (Axioma Ω₂, Ω₃) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Epistemic Breaker Daemon: %s", e)

    def _init_persistence_checkers(self, file_config: dict) -> None:
        """Initialize checks related to data persistence and timing."""
        self.engine_health = EngineHealthCheck(Path(file_config.get("db_path", str(CORTEX_DB))))
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )
        self.cloud_sync_monitor = CloudSyncMonitor(
            interval_seconds=file_config.get("cloud_sync_interval", 15),
            engine=self._shared_engine,
        )

        self.entropic_wake_daemon = None
        if _ENTROPIC_WAKE_AVAILABLE:
            try:
                self.entropic_wake_daemon = EntropicWakeDaemon(
                    engine=self._shared_engine,
                    check_interval_hours=float(
                        file_config.get("entropic_wake_interval_hours", 4.0)
                    ),
                    zenon_threshold=float(file_config.get("zenon_threshold", 1.0)),
                )
                logger.info("🌌 Entropic Wake Daemon (VOID DAEMON) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Entropic Wake Daemon: %s", e)
        # Time Tracker
        try:
            from cortex.database.core import connect
            from cortex.extensions.timing import TimingTracker

            self.timing_conn = connect(file_config.get("db_path", str(CORTEX_DB)))
            self.tracker = TimingTracker(self.timing_conn)
        except (ImportError, sqlite3.Error) as e:
            logger.error("Failed to init TimeTracker: %s", e)
            self.tracker = None

    def _init_sovereign_subsystems(self, file_config: dict) -> None:
        """Initialize the v2.0 sovereign async subsystems."""
        # 1. Hot State — SQLite-backed KV store
        self.hot_state: HotStateDB | None = None
        if _HOT_STATE_AVAILABLE:
            try:
                self.hot_state = HotStateDB()
                logger.info("🔥 HotStateDB (SQLite KV) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init HotStateDB: %s", e)

        # 2. Event Bus (reuse existing or create)
        self._event_bus = None
        try:
            from cortex.events.bus import DistributedEventBus

            self._event_bus = DistributedEventBus()
            logger.info("📡 DistributedEventBus ENABLED")
        except ImportError:
            pass

        # 3. Scheduler — cron/interval task execution
        self.scheduler: SovereignScheduler | None = None
        if _SCHEDULER_AVAILABLE:
            try:
                self.scheduler = SovereignScheduler(
                    event_bus=self._event_bus,
                    hot_state=self.hot_state,
                    tick_interval=float(file_config.get("scheduler_tick_interval", 5.0)),
                )
                logger.info("⏱️  SovereignScheduler ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init SovereignScheduler: %s", e)

        # 4. Watchdog Hub — unified filesystem monitor
        self.watchdog_hub: WatchdogHub | None = None
        if _WATCHDOG_HUB_AVAILABLE:
            try:
                watch_paths = file_config.get(
                    "watch_paths",
                    [str(CORTEX_DIR), str(Path.home() / ".agent")],
                )
                watch_patterns = file_config.get(
                    "watch_patterns",
                    ["*.py", "*.md", "*.json", "*.yaml", "*.toml"],
                )
                self.watchdog_hub = WatchdogHub(
                    paths=watch_paths,
                    patterns=watch_patterns,
                    event_bus=self._event_bus,
                    hot_state=self.hot_state,
                )
                logger.info("👁️  WatchdogHub ENABLED (%d paths)", len(watch_paths))
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init WatchdogHub: %s", e)

        # 5. Human Callback API — REST + WebSocket sidecar
        self.callback_api: HumanCallbackAPI | None = None
        if _API_AVAILABLE and file_config.get("api_enabled", True):
            try:
                self.callback_api = HumanCallbackAPI(
                    hot_state=self.hot_state,
                    scheduler=self.scheduler,
                    event_bus=self._event_bus,
                    port=int(file_config.get("api_port", 8741)),
                )
                logger.info(
                    "🌐 Human Callback API ENABLED (port %s)", file_config.get("api_port", 8741)
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init HumanCallbackAPI: %s", e)

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
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
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
            self.hot_state.set(
                "daemon.started_at",
                datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            )

        # ─── Spawn all subsystems as async tasks ──────────────────
        tasks: list[asyncio.Task] = []

        # Core check loop (replaces the main while loop)
        tasks.append(asyncio.create_task(self._sovereign_check_loop(interval), name="CheckLoop"))

        # Scheduler
        if self.scheduler is not None:
            self._register_default_schedules()
            tasks.append(asyncio.create_task(self.scheduler.run(), name="Scheduler"))

        # WatchdogHub
        if self.watchdog_hub is not None:
            tasks.append(asyncio.create_task(self.watchdog_hub.start(), name="WatchdogHub"))

        # Human Callback API
        if self.callback_api is not None:
            tasks.append(asyncio.create_task(self.callback_api.serve(), name="CallbackAPI"))

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
            self.hot_state.set(
                "daemon.stopped_at",
                datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            )

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
    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
