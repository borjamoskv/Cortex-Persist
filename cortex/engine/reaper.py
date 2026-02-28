"""
CORTEX v5.2 — Ghost Reaper (TTL-based auto-expiry).

Purges expired ghosts from both the legacy DB table and
Songlines filesystem traces (xattrs / .songlines manifests).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.reaper")

__all__ = ["GhostReaper"]

DEFAULT_TTL_DAYS = 30


class GhostReaper:
    """TTL-based ghost expiry engine.

    Addresses Cibercentro's observation: ghosts without expiry
    persist indefinitely, potentially propagating stale context.
    """

    def __init__(self, ttl_days: int = DEFAULT_TTL_DAYS) -> None:
        if ttl_days < 1:
            raise ValueError("ttl_days must be >= 1")
        self._ttl_days = ttl_days

    # ── DB Ghosts ──────────────────────────────────────────────────

    async def reap_db_ghosts(self, conn: Any) -> int:
        """Delete expired ghosts from the legacy DB table.

        A ghost is expired if:
          - It has an explicit `expires_at` that has passed, OR
          - It has no `expires_at` and `created_at + ttl_days` has passed

        Returns:
            Number of reaped ghosts.
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self._ttl_days)
        ).strftime("%Y-%m-%dT%H:%M:%S")

        # Phase 1: Explicit TTL expiry
        cursor = await conn.execute(
            "DELETE FROM ghosts WHERE status = 'open' "
            "AND expires_at IS NOT NULL AND expires_at < ?",
            (cutoff,),
        )
        explicit_count = cursor.rowcount

        # Phase 2: Implicit TTL (no expires_at, old created_at)
        cursor = await conn.execute(
            "DELETE FROM ghosts WHERE status = 'open' "
            "AND expires_at IS NULL AND created_at < ?",
            (cutoff,),
        )
        implicit_count = cursor.rowcount

        total = explicit_count + implicit_count
        await conn.commit()

        if total > 0:
            logger.info(
                "🪦 Reaped %d expired ghosts (explicit=%d, implicit=%d, ttl=%dd)",
                total, explicit_count, implicit_count, self._ttl_days,
            )
        return total

    # ── Songlines Ghosts (filesystem xattrs) ───────────────────────

    def reap_songlines_ghosts(self, root_dir: Path | None = None) -> int:
        """Remove expired ghost traces from filesystem xattrs/manifests.

        Returns:
            Number of reaped ghost traces.
        """
        root = root_dir or Path.cwd()
        reaped = 0
        cutoff_ts = time.time() - (self._ttl_days * 86400)

        # Scan .songlines manifest files
        for manifest_path in root.rglob(".songlines"):
            reaped += self._reap_manifest(manifest_path, cutoff_ts)

        if reaped > 0:
            logger.info("🪦 Reaped %d Songlines ghost traces (ttl=%dd)", reaped, self._ttl_days)
        return reaped

    def _reap_manifest(self, manifest_path: Path, cutoff_ts: float) -> int:
        """Reap expired entries from a single .songlines manifest."""
        try:
            with open(manifest_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0

        reaped = 0
        files_to_remove: list[str] = []

        for filename, attrs in data.items():
            keys_to_remove: list[str] = []
            for key, value in attrs.items():
                if not key.startswith("user.cortex.ghost."):
                    continue
                # Check if the ghost trace is older than cutoff
                if isinstance(value, dict) and "timestamp" in value:
                    if value["timestamp"] < cutoff_ts:
                        keys_to_remove.append(key)
                elif manifest_path.stat().st_mtime < cutoff_ts:
                    # Fallback: if manifest itself is old, reap all ghosts in it
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del attrs[key]
                reaped += 1

            if not attrs:
                files_to_remove.append(filename)

        for filename in files_to_remove:
            del data[filename]

        if reaped > 0:
            try:
                with open(manifest_path, "w") as f:
                    json.dump(data, f, indent=2)
            except OSError as e:
                logger.warning("Failed to write manifest %s: %s", manifest_path, e)

        return reaped
