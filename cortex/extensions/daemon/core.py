from typing import Any
from collections.abc import Callable
'MoskvDaemon - Main daemon orchestrator.\n\nv2.0: Sovereign Async Loop - single event loop replaces N threads.\nNew subsystems: SovereignScheduler, HotStateDB, WatchdogHub, HumanCallbackAPI.\n'
import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from cortex.extensions.daemon.alerts import AlertHandlerMixin
from cortex.extensions.daemon.core_support import init_advanced_monitors, init_background_agents, init_core_monitors, init_external_oracles
from cortex.extensions.daemon.healing import HealingMixin
from cortex.extensions.daemon.loops_mixin import LoopsMixin
from cortex.extensions.daemon.models import AGENT_DIR, DEFAULT_COOLDOWN, DEFAULT_MEMORY_STALE_HOURS, DEFAULT_STALE_HOURS, STATUS_FILE, DaemonStatus
try:
    _HOT_STATE_AVAILABLE = True
except ImportError:
    _HOT_STATE_AVAILABLE = False
try:
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _SCHEDULER_AVAILABLE = False
try:
    _WATCHDOG_HUB_AVAILABLE = True
except ImportError:
    _WATCHDOG_HUB_AVAILABLE = False
try:
    _API_AVAILABLE = True
except ImportError:
    _API_AVAILABLE = False
try:
    _CENTAUR_AVAILABLE = True
except ImportError:
    _CENTAUR_AVAILABLE = False
try:
    _ENTROPIC_WAKE_AVAILABLE = True
except ImportError:
    _ENTROPIC_WAKE_AVAILABLE = False
try:
    _FRONTIER_AVAILABLE = True
except ImportError:
    _FRONTIER_AVAILABLE = False
try:
    _ZERO_PROMPTING_AVAILABLE = True
except ImportError:
    _ZERO_PROMPTING_AVAILABLE = False
try:
    _EPISTEMIC_BREAKER_AVAILABLE = True
except ImportError:
    _EPISTEMIC_BREAKER_AVAILABLE = False
__all__ = ['MoskvDaemon']
logger = logging.getLogger('moskv-daemon')
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
    ast_debt_monitor: Any
    _healed_total: int
    _failure_counts: dict[str, int]
    _shutdown: bool
    _stop_event: threading.Event
    _threads: list[threading.Thread]
    _async_engine: Any
    hot_state: Any
    _event_bus: Any
    config_dir: Path

    def __init__(self, sites: list[str] | None=None, config_dir: Path=AGENT_DIR / 'memory', stale_hours: float=DEFAULT_STALE_HOURS, memory_stale_hours: float=DEFAULT_MEMORY_STALE_HOURS, cooldown: float=DEFAULT_COOLDOWN, notify: bool=True):
        self.notify_enabled = notify
        self.config_dir = config_dir
        self._shutdown = False
        self._stop_event = threading.Event()
        self._failure_counts: dict[str, int] = {}
        self._healed_total: int = 0
        self._threads: list[threading.Thread] = []
        file_config = self._load_config()
        self._cooldown = file_config.get('cooldown', cooldown)
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
        self._run_monitor(status, 'sites', self.site_monitor, self._alert_sites, method='check_all')
        self._run_monitor(status, 'stale_ghosts', self.ghost_watcher, self._alert_ghosts)
        self._run_monitor(status, 'memory_alerts', self.memory_syncer, self._alert_memory)
        self._run_monitor(status, 'cert_alerts', self.cert_monitor, self._alert_certs)
        self._run_monitor(status, 'engine_alerts', self.engine_health, self._alert_engine)
        self._run_monitor(status, 'disk_alerts', self.disk_monitor, self._alert_disk)
        self._run_monitor(status, 'evaluation_alerts', self.evaluation_monitor, self._alert_evaluation)
        self._run_monitor(status, 'mejoralo_alerts', self.mejoralo_monitor, self._alert_mejoralo)
        self._run_monitor(status, 'compaction_alerts', self.compaction_monitor, self._alert_compaction)
        self._run_monitor(status, 'perception_alerts', self.perception_monitor, self._alert_perception)
        self._run_monitor(status, 'security_alerts', self.security_monitor, self._alert_security)
        self._run_monitor(status, 'signal_alerts', self.signal_monitor, self._alert_signals)
        self._run_monitor(status, 'cloud_sync_alerts', self.cloud_sync_monitor, self._alert_cloud_sync)
        self._run_monitor(status, 'tombstone_alerts', self.tombstone_monitor, self._alert_tombstone)
        self._run_monitor(status, 'workflow_alerts', self.workflow_monitor, self._alert_workflows)
        self._run_monitor(status, 'epistemic_alerts', self.epistemic_monitor, self._alert_workflows)
        if hasattr(self, 'ast_debt_monitor'):
            self._run_monitor(status, 'ast_alerts', self.ast_debt_monitor, self._alert_ast)
        if self.aether_monitor is not None:
            self._run_monitor(status, 'aether_alerts', self.aether_monitor, self._alert_aether)
            if hasattr(self, 'auto_immune_monitor'):
                self._run_monitor(status, 'auto_immune_alerts', self.auto_immune_monitor, self._alert_auto_immune)
        self._auto_sync(status)
        self._flush_timer()
        status.check_duration_ms = (time.monotonic() - check_start) * 1000
        self._save_status(status)
        level = '✅' if status.all_healthy else '⚠️'
        logger.info('%s Check complete in %.0fms: %d sites, %d stale ghosts, %d memory alerts', level, status.check_duration_ms, len(status.sites), len(status.stale_ghosts), len(status.memory_alerts))
        return status

    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _run_monitor(self, status: DaemonStatus, attr: str, monitor: object, alert_fn: Callable, method: str='check') -> None:
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
        except Exception as e:
            status.errors.append(f'{monitor_name} error: {e}')
            logger.exception('%s failed', monitor_name)
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
            logger.error('Failed to save status: %s', e)
