"""MoskvDaemon — Main daemon orchestrator."""

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
from cortex.extensions.daemon.healing import HealingMixin
from cortex.extensions.daemon.loops_mixin import LoopsMixin
from cortex.extensions.daemon.models import (
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
from cortex.extensions.daemon.monitors import (
    AutoImmuneMonitor,
    CertMonitor,
    CloudSyncMonitor,
    CompactionMonitor,
    DiskMonitor,
    EngineHealthCheck,
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

try:
    from cortex.extensions.aether.daemon import AetherDaemon, AetherMonitor
    from cortex.extensions.aether.queue import TaskQueue

    _AETHER_AVAILABLE = True
except ImportError:
    _AETHER_AVAILABLE = False

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
    from cortex.extensions.daemon.sidecar.telemetry.iot_oracle import IoTOracle

    _IOT_ORACLE_AVAILABLE = True
except ImportError:
    _IOT_ORACLE_AVAILABLE = False

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
            from cortex.engine_async import AsyncCortexEngine
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

    def _init_background_agents(self, file_config: dict) -> None:
        """Initialize autonomous background agents like Aether."""
        # pyright: reportCallIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false  # type: ignore[type-error]
        self._aether_daemon: Optional[AetherDaemon] = None
        self.aether_monitor: Optional[AetherMonitor] = None
        if _AETHER_AVAILABLE and file_config.get("aether_enabled", False):
            try:
                aether_queue = TaskQueue()
                self._aether_daemon = AetherDaemon(
                    queue=aether_queue,
                    poll_interval=file_config.get("aether_poll_interval", 60),
                    max_concurrent=file_config.get("aether_max_concurrent", 2),
                    llm_provider=file_config.get("aether_llm_provider", "qwen"),
                    github_token=file_config.get("aether_github_token"),
                    github_repos=file_config.get("aether_github_repos", []),
                )
                self.aether_monitor = AetherMonitor(self._aether_daemon)
                self.auto_immune_monitor = AutoImmuneMonitor(queue=aether_queue)
                logger.info("🤖 Aether autonomous agent ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Aether daemon: %s", e)

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
        """Run checks in a loop until stopped."""

        def _handle_signal(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            self._shutdown = True
            self._stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("🚀 MOSKV-1 Daemon starting (interval=%ds)", interval)

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

        # Health Index — autonomous monitoring
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
