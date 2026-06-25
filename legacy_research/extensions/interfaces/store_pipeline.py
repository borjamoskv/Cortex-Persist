# [C5-REAL] Exergy-Maximized
"""Store Pipeline Protocols - Decoupled contracts for the write path.

Modules implementing these protocols can be registered with the engine
at init time instead of being hardcoded into store_mixin.py.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------


@runtime_checkable
class StoreGuard(Protocol):
    """Pre-store validation gate.

    Guards run before fact insertion. A guard that rejects raises ValueError.
    Guards that pass return silently. Each guard receives the full store context
    and the active connection for DB lookups.
    """

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Validate a fact before storage.

        Raises:
            ValueError: If the guard rejects the fact.
        """
        ...


@runtime_checkable
class ContentMutator(Protocol):
    """Content transformation step in the store pipeline.

    Unlike guards (which reject), mutators transform content/meta/fact_type
    before persistence. Examples: SovereignSanitizer, BridgeGuard elevation.
    """

    async def transform(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Transform content before storage.

        Returns:
            (content, fact_type, meta) - potentially modified.
        """
        ...


@runtime_checkable
class PostStoreHook(Protocol):
    """Post-store side-effect hook.

    Runs after successful fact insertion. Failure is non-fatal (best-effort).
    Examples: signal emission, ledger checkpointing, retrieval breaker.
    """

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        """Execute post-store side effect.

        Must not raise - exceptions are logged and swallowed.
        """
        ...
