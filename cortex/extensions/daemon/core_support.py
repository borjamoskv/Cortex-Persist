# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.extensions.daemon.models import CORTEX_DB, CORTEX_DIR, DEFAULT_CERT_WARN_DAYS
from cortex.extensions.daemon.monitors import (
    AutoImmuneMonitor,
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
from cortex.extensions.daemon.monitors.ast_oracle import ASTOracleMonitor
from cortex.extensions.daemon.monitors.l2_drain import L2DrainMonitor
from cortex.extensions.daemon.sidecar.sentinel_monitor.monitor import SentinelMonitor
from cortex.extensions.daemon.sidecar.telemetry.fiat_oracle import FiatOracle

logger = logging.getLogger("moskv-daemon")

try:
    from cortex.extensions.aether.daemon import AetherDaemon, AetherMonitor
    from cortex.extensions.aether.queue import TaskQueue

    _AETHER_AVAILABLE = True
except ImportError:
    _AETHER_AVAILABLE = False

try:
    from cortex.extensions.daemon.sidecar.telemetry.iot_oracle import IoTOracle

    _IOT_ORACLE_AVAILABLE = True
except ImportError:
    _IOT_ORACLE_AVAILABLE = False


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
    daemon.l2_drain_monitor = L2DrainMonitor(
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
    daemon.ast_debt_monitor = ASTOracleMonitor(
        projects=file_config.get("ast_debt_projects", {"cortex-persist": str(Path.cwd())}),
        interval_seconds=file_config.get("ast_debt_interval", 1800),
        engine=daemon._shared_engine,
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
    daemon.tombstone_monitor = TombstoneMonitor(db_path=file_config.get("db_path", str(CORTEX_DB)))

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
        try:
            from cortex.extensions.daemon.monitors.agy2_planner import AGY2PlannerMonitor

            daemon.agy2_planner_daemon = AGY2PlannerMonitor(engine=daemon._shared_engine)
        except ImportError:
            daemon.agy2_planner_daemon = None
    except ImportError:
        daemon._async_engine = None
        daemon.ast_oracle = None
        daemon.fiat_oracle = None
        daemon.sentinel_oracle = None
        daemon.agy2_planner_daemon = None

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
        except Exception as exc:
            logger.warning("Failed to init Aether daemon: %s", exc)
