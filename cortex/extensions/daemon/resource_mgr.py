# [C5-REAL] Exergy-Maximized
import logging
from pathlib import Path

try:
    from cortex.extensions.daemon.centaur.engine import CentauroEngine
    from cortex.extensions.daemon.centaur.entropic_queue import EntropicQueue
    from cortex.extensions.daemon.centaur.heartbeat import HeartbeatDaemon

    _CENTAUR_AVAILABLE = True
except ImportError:
    _CENTAUR_AVAILABLE = False

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
    from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon

    _ENTROPIC_WAKE_AVAILABLE = True
except ImportError:
    _ENTROPIC_WAKE_AVAILABLE = False

from cortex.extensions.daemon.models import CORTEX_DB, CORTEX_DIR
from cortex.extensions.daemon.monitors import CloudSyncMonitor, DiskMonitor, EngineHealthCheck

logger = logging.getLogger("moskv-daemon")


class ResourceMgrMixin:
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
                    engine=self._shared_engine,  # type: ignore
                    metabolism_interval_hours=int(
                        file_config.get("frontier_metabolism_interval_hours", 12)
                    ),
                    ingestion_interval_hours=int(
                        file_config.get("frontier_ingestion_interval_hours", 24)
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
                    engine=self._shared_engine,  # type: ignore
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
                    engine=self._shared_engine,  # type: ignore
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

    def _init_sovereign_subsystems(self, file_config: dict) -> None:
        """Initialize the v2.0 sovereign async subsystems."""
        # 1. Hot State — SQLite-backed KV store
        self.hot_state = None
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
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)

        # 2.5 Event Sovereignty Runtime (Hito 34)
        self.sovereignty_runtime = None
        if self._event_bus:
            try:
                from cortex.engine.causal.anomaly_bridge import AnomalyBridge
                from cortex.engine.swarm.auth_gateway import AuthGateway  # type: ignore
                from cortex.engine.temporal.event_sovereignty import EventSovereigntyRuntime

                auth_gw = AuthGateway(self._shared_engine)  # type: ignore
                # ensure table is created, though we should probably run this asynchronously,
                # but it's safe to run create table in init or async start.
                anomaly_br = AnomalyBridge()

                self.sovereignty_runtime = EventSovereigntyRuntime(
                    event_bus=self._event_bus, anomaly_bridge=anomaly_br, auth_gateway=auth_gw
                )
                logger.info("👑 EventSovereigntyRuntime ENABLED")
            except Exception as e:
                logger.warning("Failed to init EventSovereigntyRuntime: %s", e)

        # 3. Scheduler — cron/interval task execution
        self.scheduler = None
        if _SCHEDULER_AVAILABLE:
            try:
                self.scheduler = SovereignScheduler(
                    event_bus=self._event_bus,
                    hot_state=self.hot_state,
                    tick_interval=float(file_config.get("scheduler_tick_interval", 5.0)),
                    engine=self._shared_engine,  # type: ignore
                )
                logger.info("⏱️  SovereignScheduler ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init SovereignScheduler: %s", e)

        # 4. Watchdog Hub — unified filesystem monitor
        self.watchdog_hub = None
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
        self.callback_api = None
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

    def _init_persistence_checkers(self, file_config: dict) -> None:
        """Initialize checks related to data persistence and timing."""
        self.engine_health = EngineHealthCheck(Path(file_config.get("db_path", str(CORTEX_DB))))
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", 500),
        )
        self.cloud_sync_monitor = CloudSyncMonitor(
            interval_seconds=file_config.get("cloud_sync_interval", 15),
            engine=self._shared_engine,  # type: ignore
        )

        self.entropic_wake_daemon = None
        if _ENTROPIC_WAKE_AVAILABLE:
            try:
                self.entropic_wake_daemon = EntropicWakeDaemon(
                    engine=self._shared_engine,  # type: ignore
                    check_interval_hours=int(file_config.get("entropic_wake_interval_hours", 4)),
                    zenon_threshold=float(file_config.get("zenon_threshold", 1.0)),
                )
                logger.info("🌌 Entropic Wake Daemon (VOID DAEMON) ENABLED")
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to init Entropic Wake Daemon: %s", e)
        # Time Tracker
        try:
            import sqlite3

            from cortex.database.core import connect
            from cortex.extensions.timing import TimingTracker

            self.timing_conn = connect(file_config.get("db_path", str(CORTEX_DB)))
            self.tracker = TimingTracker(self.timing_conn)
        except (ImportError, sqlite3.Error) as e:
            logger.error("Failed to init TimeTracker: %s", e)
            self.tracker = None
