"""CORTEX v8.0 — Error→Ghost Pipeline (Ω₅ Antifragile Autopersistence).

Every uncaught error in the daemon/swarm is automatically persisted as a
ghost fact in cortex.db. This ensures CORTEX cannot die silently — every
failure forges an antibody.

Architecture:
  - Ring-buffer content-hash dedup (last 64 errors) prevents ghost storms.
  - Per-source rate limiting (max 1 ghost per source per 60s).
  - Thread-safe + async-safe via threading.Lock (no asyncio.Lock needed
    since we run from both sync and async contexts across threads).
  - Falls back to filesystem-based ghost persistence if DB is unreachable.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import traceback
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.swarm.error_ghost_pipeline")

# ── Constants ──────────────────────────────────────────────────────────
_DEDUP_WINDOW_SIZE = 64          # Ring buffer: last N error hashes
_RATE_LIMIT_SECONDS = 60.0       # Min interval between ghosts from same source
_FALLBACK_DIR_NAME = ".error_ghosts"


@dataclass(frozen=True)
class GhostRecord:
    """Immutable record of a persisted error ghost."""
    fact_id: int
    source: str
    error_type: str
    content_hash: str
    timestamp: float


class ErrorGhostPipeline:
    """Singleton-pattern error→ghost autopersistence engine.

    Usage (async):
        pipeline = ErrorGhostPipeline()
        await pipeline.capture(error, source="daemon:SiteMonitor", project="CORTEX")

    Usage (sync — from daemon threads):
        pipeline.capture_sync(error, source="daemon:SiteMonitor", project="CORTEX")
    """

    _instance: ErrorGhostPipeline | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> ErrorGhostPipeline:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._lock = threading.Lock()
        # OrderedDict used as LRU ring buffer for content hashes
        self._seen_hashes: OrderedDict[str, float] = OrderedDict()
        # Per-source last-emit timestamps for rate limiting
        self._rate_limits: dict[str, float] = {}
        # Stats
        self._total_captured: int = 0
        self._total_deduped: int = 0
        self._total_rate_limited: int = 0
        self._initialized = True

    # ── Public API ─────────────────────────────────────────────────────

    async def capture(
        self,
        error: BaseException,
        source: str,
        project: str = "CORTEX",
        *,
        extra_meta: dict[str, Any] | None = None,
    ) -> int | None:
        """Persist an error as a ghost fact. Returns fact_id or None."""
        content, content_hash, meta = self._prepare(error, source, extra_meta)

        if self._should_suppress(content_hash, source):
            return None

        fact_id = await self._persist_async(project, content, source, meta)
        self._record_emission(content_hash, source, fact_id)
        return fact_id

    def capture_sync(
        self,
        error: BaseException,
        source: str,
        project: str = "CORTEX",
        *,
        extra_meta: dict[str, Any] | None = None,
    ) -> None:
        """Fire-and-forget sync capture for daemon threads."""
        content, content_hash, meta = self._prepare(error, source, extra_meta)

        if self._should_suppress(content_hash, source):
            return

        # Fire in background — ghost persistence must never block the daemon
        thread = threading.Thread(
            target=self._persist_sync,
            args=(project, content, source, meta, content_hash),
            name=f"ghost-persist-{content_hash[:8]}",
            daemon=True,
        )
        thread.start()

    @property
    def stats(self) -> dict[str, int]:
        """Pipeline health stats."""
        with self._lock:
            return {
                "total_captured": self._total_captured,
                "total_deduped": self._total_deduped,
                "total_rate_limited": self._total_rate_limited,
                "dedup_window_size": len(self._seen_hashes),
            }

    def reset(self) -> None:
        """Reset pipeline state. Primarily for testing."""
        with self._lock:
            self._seen_hashes.clear()
            self._rate_limits.clear()
            self._total_captured = 0
            self._total_deduped = 0
            self._total_rate_limited = 0

    # ── Internal ───────────────────────────────────────────────────────

    def _prepare(
        self,
        error: BaseException,
        source: str,
        extra_meta: dict[str, Any] | None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Build ghost content and metadata from an error."""
        error_type = type(error).__qualname__
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb[-3:])  # Last 3 frames — enough for diagnosis

        content = (
            f"AUTO-GHOST [{source}] {error_type}: {error}\n"
            f"Traceback (last 3 frames):\n{tb_str}"
        )

        content_hash = hashlib.sha256(
            f"{source}:{error_type}:{error}".encode()
        ).hexdigest()[:16]

        meta: dict[str, Any] = {
            "error_type": error_type,
            "source": source,
            "pipeline": "error_ghost_v1",
            "content_hash": content_hash,
            "timestamp": time.time(),
        }
        if extra_meta:
            meta.update(extra_meta)

        return content, content_hash, meta

    def _should_suppress(self, content_hash: str, source: str) -> bool:
        """Check dedup window and rate limits. Thread-safe."""
        now = time.monotonic()

        with self._lock:
            # 1. Content-hash dedup (ring buffer)
            if content_hash in self._seen_hashes:
                self._total_deduped += 1
                logger.debug(
                    "AUTO-GHOST deduped [%s] (seen in window)", content_hash[:8]
                )
                return True

            # 2. Per-source rate limiting
            last_emit = self._rate_limits.get(source, 0.0)
            if now - last_emit < _RATE_LIMIT_SECONDS:
                self._total_rate_limited += 1
                logger.debug(
                    "AUTO-GHOST rate-limited [%s] (%.0fs remaining)",
                    source,
                    _RATE_LIMIT_SECONDS - (now - last_emit),
                )
                return True

        return False

    def _record_emission(
        self, content_hash: str, source: str, fact_id: int | None
    ) -> None:
        """Record successful emission in dedup window and rate limiter."""
        now = time.monotonic()
        with self._lock:
            # Ring buffer eviction
            self._seen_hashes[content_hash] = now
            while len(self._seen_hashes) > _DEDUP_WINDOW_SIZE:
                self._seen_hashes.popitem(last=False)

            self._rate_limits[source] = now
            self._total_captured += 1

        logger.warning(
            "AUTO-GHOST persisted [%s] fact_id=%s from %s",
            content_hash[:8],
            fact_id,
            source,
        )

    async def _persist_async(
        self,
        project: str,
        content: str,
        source: str,
        meta: dict[str, Any],
    ) -> int | None:
        """Store ghost via CortexEngine (async path)."""
        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            fact_id = await engine.store(
                project=project,
                content=content,
                fact_type="ghost",
                tags=["auto_ghost", "error_pipeline", source.split(":")[0]],
                confidence="computed",
                source=f"error_ghost_pipeline:{source}",
                meta=meta,
            )
            return fact_id
        except Exception as e:
            logger.error("AUTO-GHOST DB persist failed, falling back to FS: %s", e)
            self._fallback_fs_persist(project, content, source, meta)
            return None

    def _persist_sync(
        self,
        project: str,
        content: str,
        source: str,
        meta: dict[str, Any],
        content_hash: str,
    ) -> None:
        """Sync persistence via asyncio.run (for daemon threads)."""
        import asyncio

        try:
            fact_id = asyncio.run(
                self._persist_async(project, content, source, meta)
            )
            self._record_emission(content_hash, source, fact_id)
        except Exception as e:
            # Last resort — never let ghost persistence crash the daemon
            logger.error("AUTO-GHOST sync persist failed: %s", e)
            self._record_emission(content_hash, source, None)

    def _fallback_fs_persist(
        self,
        project: str,
        content: str,
        source: str,
        meta: dict[str, Any],
    ) -> None:
        """Filesystem fallback when DB is unreachable."""
        from pathlib import Path
        import json

        fallback_dir = Path.home() / ".cortex" / _FALLBACK_DIR_NAME
        fallback_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{meta.get('content_hash', 'unknown')}_{int(time.time())}.json"
        payload = {
            "project": project,
            "content": content,
            "source": source,
            "meta": meta,
        }

        try:
            (fallback_dir / filename).write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            logger.info("AUTO-GHOST fallback persisted to %s", fallback_dir / filename)
        except OSError as e:
            logger.critical("AUTO-GHOST TOTAL FAILURE — cannot persist anywhere: %s", e)
