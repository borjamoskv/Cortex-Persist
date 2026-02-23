"""MoskvDaemon — Self-healing monitor mixin.

Extracted from core.py to keep file size under 300 LOC.
Handles automatic re-instantiation of monitors that fail
more than MAX_CONSECUTIVE_FAILURES times in a row.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from cortex.daemon.models import (
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
)
from cortex.daemon.monitors import (
    AutonomousMejoraloMonitor,
    CertMonitor,
    DiskMonitor,
    EngineHealthCheck,
    EntropyMonitor,
    GhostWatcher,
    MemorySyncer,
    NeuralIntentMonitor,
    PerceptionMonitor,
    SiteMonitor,
)

__all__ = ["HealingMixin"]

logger = logging.getLogger("moskv-daemon")


class HealingMixin:
    """Mixin providing self-healing capabilities for failing monitors.

    Requires the host class to have:
        - _load_config() -> dict
        - config_dir: Path
        - _shared_engine
        - _healed_total: int
        - Individual monitor attributes (site_monitor, ghost_watcher, etc.)
    """

    def _heal_monitor(self, attr: str, monitor_name: str) -> None:
        """Re-instantiate a monitor that has failed too many times.

        Called automatically by `_run_monitor` when a monitor exceeds
        MAX_CONSECUTIVE_FAILURES. Logs the healing event and increments
        the healed counter.
        """
        from cortex.daemon.core import MAX_CONSECUTIVE_FAILURES

        logger.warning(
            "🩹 Self-healing: %s failed %d times consecutively. Re-instantiating...",
            monitor_name,
            MAX_CONSECUTIVE_FAILURES,
        )

        file_config = self._load_config()
        healed = False

        try:
            healed = self._try_heal(monitor_name, file_config)
        except (ImportError, OSError, ValueError, RuntimeError) as e:
            logger.error("🩹 Self-healing FAILED for %s: %s", monitor_name, e)

        if healed:
            self._healed_total += 1
            logger.info(
                "🩹 Self-healing: %s re-instantiated OK (total healed: %d)",
                monitor_name,
                self._healed_total,
            )

    def _try_heal(self, monitor_name: str, file_config: dict) -> bool:
        """Attempt to re-instantiate a specific monitor. Returns True on success."""
        healers = {
            "SiteMonitor": self._heal_site,
            "GhostWatcher": self._heal_ghost,
            "MemorySyncer": self._heal_memory,
            "CertMonitor": self._heal_cert,
            "EngineHealthCheck": self._heal_engine,
            "DiskMonitor": self._heal_disk,
            "EntropyMonitor": self._heal_entropy,
            "AutonomousMejoraloMonitor": self._heal_mejoralo,
            "PerceptionMonitor": self._heal_perception,
            "NeuralIntentMonitor": self._heal_neural,
        }
        healer = healers.get(monitor_name)
        if healer:
            healer(file_config)
            return True
        return False

    def _heal_site(self, cfg: dict) -> None:
        self.site_monitor = SiteMonitor(cfg.get("sites", []))

    def _heal_ghost(self, cfg: dict) -> None:
        self.ghost_watcher = GhostWatcher(
            self.config_dir / "ghosts.json",
            cfg.get("stale_hours", DEFAULT_STALE_HOURS),
        )

    def _heal_memory(self, cfg: dict) -> None:
        self.memory_syncer = MemorySyncer(
            self.config_dir / "system.json",
            cfg.get("memory_stale_hours", DEFAULT_MEMORY_STALE_HOURS),
        )

    def _heal_cert(self, cfg: dict) -> None:
        sites = cfg.get("sites", [])
        hostnames = [
            h.replace("https://", "").replace("http://", "").split("/")[0]
            for h in sites
            if h.startswith("https://")
        ]
        self.cert_monitor = CertMonitor(
            hostnames, cfg.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS)
        )

    def _heal_engine(self, cfg: dict) -> None:
        self.engine_health = EngineHealthCheck(Path(cfg.get("db_path", str(CORTEX_DB))))

    def _heal_disk(self, cfg: dict) -> None:
        self.disk_monitor = DiskMonitor(
            Path(cfg.get("watch_path", str(CORTEX_DIR))),
            cfg.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )

    def _heal_entropy(self, cfg: dict) -> None:
        self.entropy_monitor = EntropyMonitor(
            projects=cfg.get("entropy_projects", cfg.get("auto_mejoralo_projects", {})),
            interval_seconds=cfg.get("entropy_interval", 1800),
            threshold=90,
            engine=self._shared_engine,
        )

    def _heal_mejoralo(self, cfg: dict) -> None:
        self.auto_mejoralo = AutonomousMejoraloMonitor(
            projects=cfg.get("auto_mejoralo_projects", {}),
            interval_seconds=cfg.get("auto_mejoralo_interval", 1800),
            engine=self._shared_engine,
        )

    def _heal_perception(self, cfg: dict) -> None:
        self.perception_monitor = PerceptionMonitor(
            workspace=cfg.get("watch_path", str(Path.home() / "cortex")),
            interval_seconds=cfg.get("perception_interval", 300),
            engine=self._shared_engine,
        )

    def _heal_neural(self, _cfg: dict) -> None:
        self.neural_monitor = NeuralIntentMonitor()
