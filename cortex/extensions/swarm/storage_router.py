"""
StorageRouter — ΩΩ-HANDOFF Semana 5-6
Multi-backend storage fallback: Arweave → IPFS → Local.

Stores and retrieves content through a priority-ordered chain of backends.
Tracks backend health and skips degraded backends until re-probe window elapses.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "ArweaveBackend",
    "IPFSBackend",
    "LocalBackend",
    "StorageBackend",
    "StorageResult",
    "StorageRouter",
]

logger = logging.getLogger("cortex.extensions.swarm.storage_router")

# Re-probe a degraded backend after this many seconds
_REPROBE_INTERVAL: float = 60.0
# Mark backend degraded after this many consecutive failures
_FAIL_THRESHOLD: int = 2


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StorageResult:
    """Outcome of a store or retrieve operation across backends."""

    fact_id: str
    success: bool
    backends_tried: list[str] = field(default_factory=list)
    backends_succeeded: list[str] = field(default_factory=list)
    data: bytes | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class StorageBackend(Protocol):
    """Pluggable storage backend contract."""

    name: str

    async def store(self, fact_id: str, data: bytes) -> bool:
        """Persist data. Returns True on success."""
        ...

    async def retrieve(self, fact_id: str) -> bytes | None:
        """Retrieve data. Returns None if not found."""
        ...

    async def is_healthy(self) -> bool:
        """Fast health probe (no side effects)."""
        ...


# ---------------------------------------------------------------------------
# Concrete backends
# ---------------------------------------------------------------------------


class ArweaveBackend:
    """Wraps ArweaveClient as a StorageBackend."""

    name = "arweave"

    def __init__(self, arweave_client: object | None = None) -> None:
        self._client = arweave_client

    async def store(self, fact_id: str, data: bytes) -> bool:
        if self._client is None:
            return False
        try:
            result = await self._client.anchor_handoff(  # type: ignore[attr-defined]
                fact_id=fact_id,
                payload=data.decode("utf-8", errors="replace"),
            )
            return result is not None
        except Exception as exc:  # noqa: BLE001
            logger.debug("ArweaveBackend.store failed: %s", exc)
            return False

    async def retrieve(self, fact_id: str) -> bytes | None:
        if self._client is None:
            return None
        try:
            nodes = await self._client.query_fact(fact_id)  # type: ignore[attr-defined]
            if nodes:
                return str(nodes[0]).encode()
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("ArweaveBackend.retrieve failed: %s", exc)
            return None

    async def is_healthy(self) -> bool:
        if self._client is None:
            return False
        try:
            return await self._client.is_healthy()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return False


class IPFSBackend:
    """Wraps IPFSClient as a StorageBackend."""

    name = "ipfs"

    def __init__(self, ipfs_client: object | None = None) -> None:
        from cortex.extensions.swarm.ipfs_client import IPFSClient

        self._client = ipfs_client or IPFSClient()
        # fact_id → CID registry (in-process; production would use DB)
        self._registry: dict[str, str] = {}

    async def store(self, fact_id: str, data: bytes) -> bool:
        try:
            result = await self._client.pin(data, filename=f"{fact_id}.bin")  # type: ignore[attr-defined]
            self._registry[fact_id] = result.cid
            logger.debug("IPFSBackend.store: fact=%s cid=%s", fact_id, result.cid)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("IPFSBackend.store failed: %s", exc)
            return False

    async def retrieve(self, fact_id: str) -> bytes | None:
        cid = self._registry.get(fact_id)
        if not cid:
            return None
        try:
            return await self._client.fetch(cid)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.debug("IPFSBackend.retrieve failed: %s", exc)
            return None

    async def is_healthy(self) -> bool:
        try:
            return await self._client.is_healthy()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return False


class LocalBackend:
    """File-system backend. Always available; last-resort fallback."""

    name = "local"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / ".cortex" / "storage"
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, fact_id: str) -> Path:
        # Sanitise fact_id for filesystem use
        safe = fact_id.replace("/", "_").replace(":", "_")
        return self._base / f"{safe}.bin"

    async def store(self, fact_id: str, data: bytes) -> bool:
        try:
            self._path(fact_id).write_bytes(data)
            logger.debug("LocalBackend.store: fact=%s", fact_id)
            return True
        except OSError as exc:
            logger.debug("LocalBackend.store failed: %s", exc)
            return False

    async def retrieve(self, fact_id: str) -> bytes | None:
        p = self._path(fact_id)
        if not p.exists():
            return None
        try:
            return p.read_bytes()
        except OSError as exc:
            logger.debug("LocalBackend.retrieve failed: %s", exc)
            return None

    async def is_healthy(self) -> bool:
        return self._base.exists()


# ---------------------------------------------------------------------------
# Health tracker
# ---------------------------------------------------------------------------


@dataclass
class _BackendHealth:
    consecutive_failures: int = 0
    degraded_since: float = 0.0

    def is_degraded(self) -> bool:
        if self.consecutive_failures < _FAIL_THRESHOLD:
            return False
        return (time.monotonic() - self.degraded_since) < _REPROBE_INTERVAL

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.degraded_since = 0.0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures == _FAIL_THRESHOLD:
            self.degraded_since = time.monotonic()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class StorageRouter:
    """Priority-ordered multi-backend storage router.

    Default priority: Arweave (permanent) → IPFS (content-addressed) → Local.
    Falls back automatically when higher-priority backends fail or are degraded.

    Health model:
        - ≥2 consecutive failures → backend marked degraded for 60s
        - After 60s the backend is re-probed on the next operation
    """

    def __init__(self, backends: list[StorageBackend] | None = None) -> None:
        if backends is None:
            backends = [ArweaveBackend(), IPFSBackend(), LocalBackend()]
        self._backends: list[StorageBackend] = backends
        self._health: dict[str, _BackendHealth] = {b.name: _BackendHealth() for b in backends}

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    async def store(self, fact_id: str, data: bytes) -> StorageResult:
        """Store data across all healthy backends.

        Attempts every backend (not just the first). Returns a StorageResult
        with the list of backends that succeeded.
        """
        tried: list[str] = []
        succeeded: list[str] = []

        for backend in self._backends:
            health = self._health[backend.name]
            if health.is_degraded():
                logger.debug("StorageRouter: skipping degraded backend %s", backend.name)
                continue

            tried.append(backend.name)
            ok = await backend.store(fact_id, data)
            if ok:
                health.record_success()
                succeeded.append(backend.name)
                logger.info("StorageRouter.store: %s → %s ✓", fact_id, backend.name)
            else:
                health.record_failure()
                logger.warning("StorageRouter.store: %s → %s ✗", fact_id, backend.name)

        success = len(succeeded) > 0
        return StorageResult(
            fact_id=fact_id,
            success=success,
            backends_tried=tried,
            backends_succeeded=succeeded,
            error=None if success else "all backends failed",
        )

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    async def retrieve(self, fact_id: str) -> StorageResult:
        """Retrieve data from the first backend that has it.

        Returns immediately on first success (cascade semantics).
        """
        tried: list[str] = []

        for backend in self._backends:
            health = self._health[backend.name]
            if health.is_degraded():
                continue

            tried.append(backend.name)
            try:
                data = await backend.retrieve(fact_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("StorageRouter.retrieve: %s failed: %s", backend.name, exc)
                health.record_failure()
                continue

            if data is not None:
                health.record_success()
                logger.info("StorageRouter.retrieve: %s ← %s ✓", fact_id, backend.name)
                return StorageResult(
                    fact_id=fact_id,
                    success=True,
                    backends_tried=tried,
                    backends_succeeded=[backend.name],
                    data=data,
                )

        return StorageResult(
            fact_id=fact_id,
            success=False,
            backends_tried=tried,
            backends_succeeded=[],
            error=f"not found in any backend (tried: {tried})",
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def backend_status(self) -> dict[str, dict[str, object]]:
        """Snapshot of backend health states."""
        return {
            b.name: {
                "degraded": self._health[b.name].is_degraded(),
                "consecutive_failures": self._health[b.name].consecutive_failures,
            }
            for b in self._backends
        }
