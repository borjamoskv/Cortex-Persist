"""Initialization helpers for the main daemon orchestrator."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from cortex.extensions.daemon.models import (
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_DISK_WARN_MB,
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

logger = logging.getLogger("moskv-daemon")

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
    from cortex.extensions.daemon.autopoiesis import AutopoiesisDaemon

    _AUTOPOIESIS_AVAILABLE = True
except ImportError:
    _AUTOPOIESIS_AVAILABLE = False

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


def init_core_monitors(
    daemon: Any,
    file_config: dict[str, Any],
    sites: list[str] | None,
    stale_hours: float,
    memory_stale_hours: float,
) -> None:
    """Initialize basic status monitors."""
    resolved_sites = sites or file_config.get("sites", [])
    daemon.site_monitor = SiteMonitor(resolved_sites)
    daemon.ghost_watcher = GhostWatcher(
        daemon.config_dir / "ghosts.json",
        file_config.get("stale_hours", stale_hours),
    )
    daemon.memory_syncer = MemorySyncer(
        daemon.config_dir / "system.json",
        file_config.get("memory_stale_hours", memory_stale_hours),
    )
    daemon.evaluation_monitor = EvaluationMonitor(db_path=CORTEX_DB)
    try:
        from cortex.engine import CortexEngine

        daemon._shared_engine = CortexEngine()
    except ImportError:
        daemon._shared_engine = None


def init_advanced_monitors(daemon: Any, file_config: dict[str, Any]) -> None:
    """Initialize optimization and analysis monitors."""
    daemon.mejoralo_monitor = UnifiedMejoraloMonitor(
        projects=file_config.get("auto_mejoralo_projects", {}),
        interval_seconds=file_config.get("auto_mejoralo_interval", 1800),
        threshold=90,
        engine=daemon._shared_engine,
        auto_heal=True,
    )
    daemon.compaction_monitor = CompactionMonitor(
        projects=list(file_config.get("auto_mejoralo_projects", {}).keys()),
        interval_seconds=file_config.get("compaction_interval", 28800),
        engine=daemon._shared_engine,
    )
    daemon.perception_monitor = PerceptionMonitor(
        workspace=file_config.get("watch_path", str(Path.home() / "cortex")),
        interval_seconds=file_config.get("perception_interval", 300),
        engine=daemon._shared_engine,
    )
    daemon.neural_monitor = NeuralIntentMonitor()
    daemon.security_monitor = SecurityMonitor(
        log_path=file_config.get("security_log_path", "~/.cortex/firewall.log"),
        threshold=file_config.get("security_threshold", 0.85),
    )
    daemon.workflow_monitor = WorkflowMonitor(
        ghosts_path=daemon.config_dir / "ghosts.json",
        memory_path=daemon.config_dir / "system.json",
        db_path=Path(file_config.get("db_path", str(CORTEX_DB))),
    )
    daemon.epistemic_monitor = EpistemicMonitor(
        engine=daemon._shared_engine,
        eval_interval_seconds=file_config.get("epistemic_eval_interval", 600),
        critical_repair_threshold=file_config.get("epistemic_repair_threshold", 5),
        decay_velocity_threshold=file_config.get("epistemic_decay_threshold", -0.05),
        stale_ratio_threshold=file_config.get("epistemic_stale_ratio", 0.20),
    )


def init_external_oracles(
    daemon: Any,
    file_config: dict[str, Any],
    resolved_sites: list[str],
) -> None:
    """Initialize external monitors and oracle integrations."""
    daemon.signal_monitor = SignalMonitor(
        db_path=file_config.get("db_path", str(CORTEX_DB)),
        engine=daemon._shared_engine,
    )
    daemon.tombstone_monitor = TombstoneMonitor(
        db_path=file_config.get("db_path", str(CORTEX_DB))
    )

    try:
        from cortex.database.pool import CortexConnectionPool
        from cortex.engine import CortexEngine as AsyncCortexEngine
        from cortex.extensions.daemon.sidecar.telemetry import ASTOracle

        db_path = file_config.get("db_path", str(CORTEX_DB))
        pool = CortexConnectionPool(db_path)
        daemon._async_engine = AsyncCortexEngine(pool=pool, db_path=db_path)
        daemon.ast_oracle = ASTOracle(
            engine=daemon._async_engine,
            watch_dir=Path(file_config.get("watch_path", str(CORTEX_DIR))),
        )
        if _IOT_ORACLE_AVAILABLE:
            daemon.iot_oracle = IoTOracle(
                engine=daemon._async_engine,
                poll_interval=float(file_config.get("iot_interval", 10.0)),
                enable_simulated_sensors=file_config.get("iot_simulated", True),
            )
        daemon.fiat_oracle = FiatOracle(
            engine=daemon._shared_engine,
            interval=file_config.get("fiat_interval", 30.0),
        )
        daemon.sentinel_oracle = SentinelMonitor(
            check_interval=file_config.get("sentinel_interval", 60),
        )
    except ImportError:
        daemon._async_engine = None
        daemon.ast_oracle = None
        daemon.fiat_oracle = None
        daemon.sentinel_oracle = None

    cert_hostnames = [
        host.replace("https://", "").replace("http://", "").split("/")[0]
        for host in resolved_sites
        if host.startswith("https://")
    ]
    daemon.cert_monitor = CertMonitor(
        cert_hostnames,
        file_config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS),
    )


def init_background_agents(daemon: Any, file_config: dict[str, Any]) -> None:
    """Initialize autonomous background agents like Aether."""
    daemon._aether_daemon = None
    daemon.aether_monitor = None
    if _AETHER_AVAILABLE and file_config.get("aether_enabled", False):
        try:
            aether_queue = TaskQueue()
            daemon._aether_daemon = AetherDaemon(
                queue=aether_queue,
                poll_interval=file_config.get("aether_poll_interval", 60),
                max_concurrent=file_config.get("aether_max_concurrent", 2),
                llm_provider=file_config.get("aether_llm_provider", "qwen"),
                github_token=file_config.get("aether_github_token"),
                github_repos=file_config.get("aether_github_repos", []),
            )
            daemon.aether_monitor = AetherMonitor(daemon._aether_daemon)
            daemon.auto_immune_monitor = AutoImmuneMonitor(queue=aether_queue)
            logger.info("🤖 Aether autonomous agent ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Aether daemon: %s", exc)


def init_autopoiesis(daemon: Any, file_config: dict[str, Any]) -> None:
    """Initialize heartbeat and self-improvement engines."""
    daemon.heartbeat_daemon = None
    if _CENTAUR_AVAILABLE:
        try:
            db_path = file_config.get("db_path", str(CORTEX_DB))
            centaur_queue = EntropicQueue(db_path=Path(db_path).parent / "entropic_queue.db")
            centauro_engine = CentauroEngine()
            daemon.heartbeat_daemon = HeartbeatDaemon(
                queue=centaur_queue,
                engine=centauro_engine,
                poll_interval=float(file_config.get("heartbeat_interval", 30.0)),
            )
            logger.info("❤️  HeartbeatDaemon (Continuous Autopoiesis) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init HeartbeatDaemon: %s", exc)

    daemon.frontier_daemon = None
    if _FRONTIER_AVAILABLE:
        try:
            daemon.frontier_daemon = FrontierDaemon(
                engine=daemon._shared_engine,
                metabolism_interval_hours=int(
                    float(file_config.get("frontier_metabolism_interval_hours", 12.0))
                ),
                ingestion_interval_hours=int(
                    float(file_config.get("frontier_ingestion_interval_hours", 24.0))
                ),
                allow_commits=file_config.get("frontier_allow_commits", True),
            )
            logger.info("🚀 Frontier Daemon (Evolution Engine) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Frontier Daemon: %s", exc)

    daemon.zero_prompting_daemon = None
    if _ZERO_PROMPTING_AVAILABLE:
        try:
            daemon.zero_prompting_daemon = ZeroPromptingDaemon(
                engine=daemon._shared_engine,
                workspace_root=Path(file_config.get("watch_path", str(CORTEX_DIR))),
                cycle_interval_hours=float(file_config.get("zero_prompting_interval_hours", 24.0)),
            )
            logger.info("🧠 Zero-Prompting Evolution Daemon (Axioma Ω₇) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Zero-Prompting Daemon: %s", exc)

    daemon.autopoiesis_daemon = None
    if _AUTOPOIESIS_AVAILABLE:
        try:
            daemon.autopoiesis_daemon = AutopoiesisDaemon(
                engine=daemon._shared_engine,
                workspace_root=Path(file_config.get("watch_path", str(CORTEX_DIR))),
                cycle_interval_hours=float(file_config.get("autopoiesis_interval_hours", 24.0)),
                idle_poll_seconds=float(file_config.get("autopoiesis_idle_poll_seconds", 60.0)),
                target_score=int(file_config.get("autopoiesis_target_score", 95)),
                enable_healing=bool(file_config.get("autopoiesis_enable_healing", True)),
                enable_manifestation=bool(
                    file_config.get("autopoiesis_enable_manifestation", False)
                ),
                minimum_registered_tools=int(
                    file_config.get("autopoiesis_minimum_registered_tools", 0)
                ),
                project=str(file_config.get("autopoiesis_project", "cortex")),
                focus=str(file_config.get("autopoiesis_focus", "entropy")),
            )
            logger.info("♾️ Autopoiesis Daemon (Bounded Self-Improvement) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Autopoiesis Daemon: %s", exc)

    daemon.epistemic_breaker_daemon = None
    if _EPISTEMIC_BREAKER_AVAILABLE:
        try:
            daemon.epistemic_breaker_daemon = EpistemicBreakerDaemon(
                engine=daemon._shared_engine,
                check_interval_seconds=int(
                    file_config.get("epistemic_breaker_interval_seconds", 300)
                ),
                max_entropy_threshold=float(file_config.get("epistemic_breaker_max_entropy", 0.85)),
            )
            logger.info("🛡️ Sovereign Epistemic Circuit Breaker (Axioma Ω₂, Ω₃) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Epistemic Breaker Daemon: %s", exc)


def init_persistence_checkers(daemon: Any, file_config: dict[str, Any]) -> None:
    """Initialize checks related to persistence and timing."""
    daemon.engine_health = EngineHealthCheck(Path(file_config.get("db_path", str(CORTEX_DB))))
    daemon.disk_monitor = DiskMonitor(
        Path(file_config.get("watch_path", str(CORTEX_DIR))),
        file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
    )
    daemon.cloud_sync_monitor = CloudSyncMonitor(
        interval_seconds=file_config.get("cloud_sync_interval", 15),
        engine=daemon._shared_engine,
    )

    daemon.entropic_wake_daemon = None
    if _ENTROPIC_WAKE_AVAILABLE:
        try:
            daemon.entropic_wake_daemon = EntropicWakeDaemon(
                engine=daemon._shared_engine,
                check_interval_hours=int(
                    float(file_config.get("entropic_wake_interval_hours", 4.0))
                ),
                zenon_threshold=float(file_config.get("zenon_threshold", 1.0)),
            )
            logger.info("🌌 Entropic Wake Daemon (VOID DAEMON) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init Entropic Wake Daemon: %s", exc)

    try:
        from cortex.database.core import connect
        from cortex.extensions.timing import TimingTracker

        daemon.timing_conn = connect(file_config.get("db_path", str(CORTEX_DB)))
        daemon.tracker = TimingTracker(daemon.timing_conn)
    except (ImportError, sqlite3.Error) as exc:
        logger.error("Failed to init TimeTracker: %s", exc)
        daemon.tracker = None


def init_sovereign_subsystems(daemon: Any, file_config: dict[str, Any]) -> None:
    """Initialize the v2.0 sovereign async subsystems."""
    daemon.hot_state = None
    if _HOT_STATE_AVAILABLE:
        try:
            daemon.hot_state = HotStateDB()
            logger.info("🔥 HotStateDB (SQLite KV) ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init HotStateDB: %s", exc)

    daemon._event_bus = None
    try:
        from cortex.events.bus import DistributedEventBus

        daemon._event_bus = DistributedEventBus()
        logger.info("📡 DistributedEventBus ENABLED")
    except ImportError:
        pass

    daemon.scheduler = None
    if _SCHEDULER_AVAILABLE:
        try:
            daemon.scheduler = SovereignScheduler(
                event_bus=daemon._event_bus,
                hot_state=daemon.hot_state,
                tick_interval=float(file_config.get("scheduler_tick_interval", 5.0)),
            )
            logger.info("⏱️  SovereignScheduler ENABLED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init SovereignScheduler: %s", exc)

    daemon.watchdog_hub = None
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
            daemon.watchdog_hub = WatchdogHub(
                paths=watch_paths,
                patterns=watch_patterns,
                event_bus=daemon._event_bus,
                hot_state=daemon.hot_state,
            )
            logger.info("👁️  WatchdogHub ENABLED (%d paths)", len(watch_paths))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init WatchdogHub: %s", exc)

    daemon.callback_api = None
    if _API_AVAILABLE and file_config.get("api_enabled", True):
        try:
            daemon.callback_api = HumanCallbackAPI(
                hot_state=daemon.hot_state,
                scheduler=daemon.scheduler,
                event_bus=daemon._event_bus,
                port=int(file_config.get("api_port", 8741)),
            )
            logger.info(
                "🌐 Human Callback API ENABLED (port %s)", file_config.get("api_port", 8741)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init HumanCallbackAPI: %s", exc)
