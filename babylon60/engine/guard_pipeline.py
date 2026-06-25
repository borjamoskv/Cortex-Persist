# [C5-REAL] Exergy-Maximized
"""Guard Pipeline - Composable pre-store, mutate, and post-store chain.

Replaces the hardcoded try/except ImportError blocks in store_mixin._store_impl
with a registered list of protocol-conforming guards, mutators, and hooks.

Guards that fail to import at registration time are silently skipped.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from babylon60.extensions.interfaces.store_pipeline import (
        ContentMutator,
        PostStoreHook,
        StoreGuard,
    )

__all__ = ["GuardPipeline"]

logger = logging.getLogger("babylon60.engine")


class GuardPipeline:
    """Orchestrates pre-store guards, content mutators, and post-store hooks."""

    def __init__(self) -> None:
        self._guards: list[StoreGuard] = []
        self._mutators: list[ContentMutator] = []
        self._post_hooks: list[PostStoreHook] = []

    # ─── Registration ─────────────────────────────────────────────

    def add_guard(self, guard: StoreGuard) -> None:
        self._guards.append(guard)

    def add_mutator(self, mutator: ContentMutator) -> None:
        self._mutators.append(mutator)

    def add_post_hook(self, hook: PostStoreHook) -> None:
        self._post_hooks.append(hook)

    # ─── Execution ────────────────────────────────────────────────

    async def run_guards(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Run all pre-store guards. First rejection raises ValueError."""
        for guard in self._guards:
            await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)

    async def run_mutators(
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
        """Run all content mutators in order. Each receives the previous output."""
        for mutator in self._mutators:
            content, fact_type, meta = await mutator.transform(
                content,
                project,
                fact_type,
                meta,
                conn,
                tenant_id=tenant_id,
                source=source,
            )
        return content, fact_type, meta

    async def run_post_hooks(
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
        """Run all post-store hooks. Failures are logged but never raised."""
        for hook in self._post_hooks:
            try:
                await hook.on_stored(
                    fact_id,
                    project,
                    fact_type,
                    conn,
                    tenant_id=tenant_id,
                    source=source,
                    db_path=db_path,
                )
            except Exception as e:
                logger.debug(
                    "[GuardPipeline] Post-hook %s failed: %s",
                    type(hook).__name__,
                    e,
                )

    @property
    def guard_count(self) -> int:
        return len(self._guards)

    @property
    def mutator_count(self) -> int:
        return len(self._mutators)

    @property
    def hook_count(self) -> int:
        return len(self._post_hooks)
