"""Tuning Persistence — Save and Restore Learned Optimizations.

Persists L6 Self-Optimizer tunings to disk so the system retains
its learned parameter optimizations across restarts.

Storage format: JSON (human-readable, git-diffable).
Location: project_root/.cortex/tunings/<subsystem>.json

Reality Level: C5-REAL
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

__all__ = ["TuningStore"]

logger = logging.getLogger("cortex.engine.tuning_store")

_DEFAULT_DIR = ".cortex/tunings"


class TuningStore:
    """Persistent storage for learned parameter optimizations.

    Saves tuning decisions to disk as JSON files, one per subsystem.
    On startup, loads previous tunings to avoid cold-start re-learning.

    Usage:
        store = TuningStore(base_dir="/path/to/project")

        # Save after optimization cycle
        store.save("api", {"timeout_ms": 8000, "batch_size": 200})

        # Load on startup
        params = store.load("api")

        # Load all
        all_params = store.load_all()

        # Snapshot entire optimizer state
        store.snapshot(optimizer.get_all_tuned_params(), optimizer.stats)
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.cwd()
        self._base = Path(base_dir) / _DEFAULT_DIR
        self._base.mkdir(parents=True, exist_ok=True)
        self._snapshot_path = self._base / "_snapshot.json"

    def save(self, subsystem: str, params: dict[str, Any]) -> Path:
        """Save tuned parameters for a subsystem."""
        path = self._subsystem_path(subsystem)
        data = {
            "subsystem": subsystem,
            "params": params,
            "saved_at": time.time(),
            "saved_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.debug("[TUNING_STORE] Saved %s → %s", subsystem, path)
        return path

    def load(self, subsystem: str) -> dict[str, Any] | None:
        """Load tuned parameters for a subsystem. Returns None if not found."""
        path = self._subsystem_path(subsystem)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return data.get("params", {})
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[TUNING_STORE] Failed to load %s: %s", subsystem, e)
            return None

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all persisted tunings. Returns {subsystem: params}."""
        result = {}
        for path in self._base.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text())
                sub = data.get("subsystem", path.stem)
                params = data.get("params", {})
                if params:
                    result[sub] = params
            except (json.JSONDecodeError, OSError):
                continue
        return result

    def delete(self, subsystem: str) -> bool:
        """Delete persisted tunings for a subsystem."""
        path = self._subsystem_path(subsystem)
        if path.exists():
            path.unlink()
            return True
        return False

    def snapshot(
        self,
        all_params: dict[str, dict[str, Any]],
        stats: dict[str, Any] | None = None,
    ) -> Path:
        """Save a complete optimizer state snapshot."""
        data = {
            "params": all_params,
            "stats": stats or {},
            "snapshot_at": time.time(),
            "snapshot_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._snapshot_path.write_text(json.dumps(data, indent=2, default=str))

        # Also save individual subsystem files
        for sub, params in all_params.items():
            self.save(sub, params)

        logger.info(
            "[TUNING_STORE] Snapshot saved: %d subsystems", len(all_params)
        )
        return self._snapshot_path

    def load_snapshot(self) -> dict[str, Any] | None:
        """Load the last optimizer snapshot."""
        if not self._snapshot_path.exists():
            return None
        try:
            return json.loads(self._snapshot_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    @property
    def subsystems(self) -> list[str]:
        """List all subsystems with persisted tunings."""
        result = []
        for path in self._base.glob("*.json"):
            if not path.name.startswith("_"):
                result.append(path.stem)
        return result

    def _subsystem_path(self, subsystem: str) -> Path:
        # Sanitize subsystem name for filesystem
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in subsystem)
        return self._base / f"{safe}.json"
