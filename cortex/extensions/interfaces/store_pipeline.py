"""Store Pipeline Protocols — Decoupled contracts for the write path.

Modules implementing these protocols can be registered with the engine
at init time instead of being hardcoded into store_mixin.py.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

import aiosqlite


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
        source: Optional[str] = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Transform content before storage.

        Returns:
            (content, fact_type, meta) — potentially modified.
        """
        ...


@runtime_checkable
class PostStoreHook(Protocol):
    """Post-store side-effect hook.

    Runs after successful fact insertion. Failure is non-fatal (best-effort).
    Examples: signal emission, ledger checkpointing, epistemic breaker.
    """

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> None:
        """Execute post-store side effect.

        Must not raise — exceptions are logged and swallowed.
        """
        ...
