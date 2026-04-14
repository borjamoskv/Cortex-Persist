"""Initializer mixin for MoskvDaemon to satisfy LOC constraints."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from cortex.extensions.daemon.models import (
    AGENT_DIR,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_COOLDOWN,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
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

logger = logging.getLogger("moskv-daemon.init")

class DaemonInitializerMixin:
    """Extracted initialization logic for MoskvDaemon."""

    def _init_core_monitors(
        self,
        file_config: dict,
        sites: Optional[list[str]],
        stale_hours: float,
        memory_stale_hours: float,
    ) -> None:
        """Initialize basic status monitors."""
        resolved_sites = sites or file_config.get("sites", [])
        self._resolved_sites = resolved_sites
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
        except Exception as e:
            self._async_engine = None
            self.ast_oracle = None
            self.fiat_oracle = None
            self.sentinel_oracle = None
            logger.warning("Failed to init external oracles: %s", e)

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
            except Exception as e:
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
            except Exception as e:
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
            except Exception as e:
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
            except Exception as e:
                logger.warning("Failed to init Zero-Prompting Daemon: %s", e)

    def _init_epistemic_breaker(self, file_config: dict) -> None:
        """Initialize the epistemic circuit breaker."""
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
            except Exception as e:
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
            except Exception as e:
                logger.warning("Failed to init Entropic Wake Daemon: %s", e)
        # Time Tracker
        try:
            from cortex.database.core import connect
            from cortex.extensions.timing import TimingTracker

            # Ω₉: Real Transaction Verification
            self.timing_conn = connect(file_config.get("db_path", str(CORTEX_DB)))
            self.tracker = TimingTracker(self.timing_conn)
        except Exception as e:
            logger.error("Failed to init TimeTracker: %s", e)
            self.tracker = None

    def _init_sovereign_subsystems(self, file_config: dict) -> None:
        """Initialize the v2.0 sovereign async subsystems."""
        # 1. Hot State — SQLite-backed KV store
        self.hot_state: Optional[HotStateDB] = None
        if _HOT_STATE_AVAILABLE:
            try:
                self.hot_state = HotStateDB()
                logger.info("🔥 HotStateDB (SQLite KV) ENABLED")
            except Exception as e:
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
        self.scheduler: Optional[SovereignScheduler] = None
        if _SCHEDULER_AVAILABLE:
            try:
                self.scheduler = SovereignScheduler(
                    event_bus=self._event_bus,
                    hot_state=self.hot_state,
                    tick_interval=float(file_config.get("scheduler_tick_interval", 5.0)),
                )
                logger.info("⏱️  SovereignScheduler ENABLED")
            except Exception as e:
                logger.warning("Failed to init SovereignScheduler: %s", e)

        # 4. Watchdog Hub — unified filesystem monitor
        self.watchdog_hub: Optional[WatchdogHub] = None
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
            except Exception as e:
                logger.warning("Failed to init WatchdogHub: %s", e)

        # 5. Human Callback API — REST + WebSocket sidecar
        self.callback_api: Optional[HumanCallbackAPI] = None
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
            except Exception as e:
                logger.warning("Failed to init HumanCallbackAPI: %s", e)
