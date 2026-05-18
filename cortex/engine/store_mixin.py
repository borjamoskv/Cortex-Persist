"""Storage Engine — store, update, deprecate, ghost management.

Converted from StoreMixin multiple-inheritance to composed StoreEngine delegate.
Security guards  → cortex.engine.store_guards
Validators/dedup → cortex.engine.store_validators
Quarantine       → cortex.engine.store_quarantine_mixin
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Optional

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.capabilities import CapabilityRegistry
from cortex.engine.embedding_engine import embed_fact_async
from cortex.engine.fact_store_core import insert_fact_record
from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.privacy_mixin import PrivacyMixin
from cortex.engine.store_mutation import (
    deprecate_impl_logic,
    invalidate_impl_logic,
    purge_logic,
)
from cortex.engine.store_quarantine_mixin import QuarantineMixin
from cortex.engine.store_validation import run_store_validation_logic
from cortex.engine.store_validators import MIN_CONTENT_LENGTH, check_dedup, validate_content
from cortex.guards.thermodynamic import AgentMode, ThermodynamicCounters

__all__ = ["StoreEngine", "StoreMixin"]

logger = logging.getLogger("cortex")


class StoreEngine:
    """Sovereign Storage Layer — Fact Lifecycle with Zero-Trust Isolation.

    Delegates all complex mutations, validations, and storage logic.
    """

    MIN_CONTENT_LENGTH = MIN_CONTENT_LENGTH

    def __init__(self, engine: Any):
        self.engine = engine

    @property
    def _engine(self) -> Any:
        """Resolve either the delegated engine reference or self if called as a legacy mixin."""
        return getattr(self, "engine", self)

    def _resolve_tenant(self, tenant_id: str) -> str:
        return self._engine._resolve_tenant(tenant_id)

    def session(self):
        return self._engine.session()

    async def _log_transaction(self, *args, **kwargs):
        return await self._engine._log_transaction(*args, **kwargs)

    def _get_embedder(self):
        return self._engine._get_embedder()

    async def store(
        self,
        project: str,
        content: str,
        tenant_id: str = "default",
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        valid_from: str | None = None,
        commit: bool = True,
        tx_id: int | None = None,
        parent_decision_id: int | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """Store a new fact with proper connection management."""
        tenant_id = self._resolve_tenant(tenant_id)

        # ═══ SOVEREIGN LOCK (Axiom Ω_CB) ═══
        if getattr(self._engine, "system_state", "ACTIVE") == "LOCKED_EPISTEMIC_HALT":
            if source != "daemon:circuit-breaker":
                raise RuntimeError(
                    "CORTEX Engine is in LOCKED_EPISTEMIC_HALT state due to cognitive thrashing. "
                    "Write access denied until Sovereign Lock is lifted by Autodidact-Omega."
                )

        if conn:
            return await self._store_impl(
                conn,
                project=project,
                content=content,
                tenant_id=tenant_id,
                fact_type=fact_type,
                tags=tags,
                confidence=confidence,
                source=source,
                meta=meta,
                valid_from=valid_from,
                commit=commit,
                tx_id=tx_id,
                parent_decision_id=parent_decision_id,
            )

        async with self.session() as _conn:
            return await self._store_impl(
                _conn,
                project=project,
                content=content,
                tenant_id=tenant_id,
                fact_type=fact_type,
                tags=tags,
                confidence=confidence,
                source=source,
                meta=meta,
                valid_from=valid_from,
                commit=commit,
                tx_id=tx_id,
                parent_decision_id=parent_decision_id,
            )

    async def _run_store_validation(
        self,
        conn: aiosqlite.Connection,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str] | None,
        confidence: str,
        source: str | None,
        meta: dict[str, Any] | None,
    ) -> tuple[int | None, dict[str, Any] | None, str, str]:
        """Delegated validation logic (Ω₁₃, Semantic Dedup, Bridge)."""
        return await run_store_validation_logic(
            mixin_instance=self._engine,
            conn=conn,
            project=project,
            content=content,
            tenant_id=tenant_id,
            fact_type=fact_type,
            tags=tags,
            confidence=confidence,
            source=source,
            meta=meta,
        )

    async def _store_impl(
        self,
        conn: aiosqlite.Connection,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str] | None,
        confidence: str,
        source: str | None,
        meta: dict[str, Any] | None,
        valid_from: str | None,
        commit: bool,
        tx_id: int | None,
        parent_decision_id: int | None = None,
    ) -> int:
        # ═══ AX-II: Pre-store guards via GuardPipeline ═══
        pipeline = getattr(self._engine, "_guard_pipeline", None)
        if pipeline is not None:
            try:
                await pipeline.run_guards(
                    content, project, fact_type, meta or {}, conn, tenant_id=tenant_id
                )
            except ValueError:
                raise  # Guard rejections must propagate
            except Exception as _gp_err:  # noqa: BLE001
                logger.debug("[AX-II] GuardPipeline pre-store skipped: %s", _gp_err)

        dedupe_id, meta, content, fact_type = await self._run_store_validation(
            conn, project, content, tenant_id, fact_type, tags, confidence, source, meta
        )
        if dedupe_id is not None:
            return dedupe_id

        tx_id = (
            tx_id
            if tx_id is not None
            else await self._log_transaction(
                conn,
                project,
                "store",
                {"fact_type": fact_type},
                tenant_id=tenant_id,
            )
        )
        fact_id = await insert_fact_record(
            conn,
            tenant_id,
            project,
            content,
            fact_type,
            tags,
            confidence,
            valid_from,
            source,
            meta,
            tx_id,
            parent_decision_id=parent_decision_id,
        )

        caps = CapabilityRegistry.get_instance().capabilities
        if (
            getattr(self._engine, "_auto_embed", False)
            and getattr(self._engine, "_vec_available", False)
            and caps.embeddings
        ):
            await embed_fact_async(
                conn,
                fact_id,
                project,
                content,
                self._get_embedder(),
                getattr(self._engine, "_memory_manager", None),
                tenant_id,
            )

        if commit:
            await conn.commit()

        # ═══ AX-II: Post-store hooks via GuardPipeline ═══
        if pipeline is not None:
            db_path = str(getattr(self._engine, "_db_path", "") or "")
            try:
                await pipeline.run_post_hooks(
                    fact_id,
                    project,
                    fact_type,
                    conn,
                    tenant_id=tenant_id,
                    source=source,
                    db_path=db_path,
                )
            except Exception as _ph_err:  # noqa: BLE001
                logger.debug("[AX-II] GuardPipeline post-hooks skipped: %s", _ph_err)

        return fact_id

    async def store_many(self, facts: list[dict[str, Any]]) -> list[int]:
        if not facts:
            raise ValueError("facts list cannot be empty")
        async with self.session() as conn:
            ids = []
            try:
                for fact in facts:
                    ids.append(await self.store(commit=False, conn=conn, **fact))
                await conn.commit()
                return ids
            except (aiosqlite.Error, ValueError, OSError):
                # Deliberate boundary: rollback any store failure atomically, then re-raise
                await conn.rollback()
                raise

    async def update(
        self,
        fact_id: int,
        content: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> int:
        tenant_id = self._resolve_tenant(tenant_id)

        async with self.session() as conn:
            query = (
                "SELECT tenant_id, project, content, fact_type, "
                "confidence, source, metadata "
                "FROM facts WHERE id = ? AND tenant_id = ? AND is_tombstoned = 0"
            )
            async with conn.execute(query, (fact_id, tenant_id)) as cursor:
                row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Fact {fact_id} not found or belongs to another tenant")

            (
                db_tenant_id,
                project,
                raw_old_content,
                fact_type,
                confidence,
                source,
                raw_old_meta_json,
            ) = row

            # Fetch tags from bridge table
            async with conn.execute(
                "SELECT tag FROM fact_tags WHERE fact_id = ? AND tenant_id = ?",
                (fact_id, db_tenant_id),
            ) as cursor:
                tag_rows = await cursor.fetchall()
                old_tags = [r[0] for r in tag_rows]

            enc = get_default_encrypter()
            old_content = (
                enc.decrypt_str(raw_old_content, tenant_id=db_tenant_id) if raw_old_content else ""
            )
            new_meta: dict[str, Any] = (
                enc.decrypt_json(raw_old_meta_json, tenant_id=db_tenant_id)
                if raw_old_meta_json
                else {}
            ) or {}
            if meta:
                new_meta.update(meta)
            new_meta["previous_fact_id"] = fact_id

            # Deprecate first to avoid unique constraint violations on identical hashes
            await self.deprecate(fact_id, reason="updated", conn=conn, tenant_id=db_tenant_id)

            new_id = await self.store(
                project=project,
                content=content if content is not None else str(old_content or ""),
                tenant_id=db_tenant_id,
                fact_type=fact_type,
                tags=tags if tags is not None else old_tags,
                confidence=confidence,
                source=source or "engine:update",
                meta=new_meta,
                conn=conn,
                commit=False,
            )

            await conn.commit()
            return new_id

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        conn: aiosqlite.Connection | None = None,
        tenant_id: str = "default",
    ) -> bool:
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        tenant_id = self._resolve_tenant(tenant_id)

        if conn:
            return await self._deprecate_impl(conn, fact_id, reason, tenant_id)

        import typing

        async with self.session() as _raw_conn:
            _conn = typing.cast(aiosqlite.Connection, _raw_conn)
            res = await self._deprecate_impl(_conn, fact_id, reason, tenant_id)
            await _conn.commit()
            return res

    async def _deprecate_impl(
        self, conn: aiosqlite.Connection, fact_id: int, reason: str | None, tenant_id: str
    ) -> bool:
        """Delegated deprecation logic."""
        return await deprecate_impl_logic(
            mixin_instance=self._engine,
            conn=conn,
            fact_id=fact_id,
            reason=reason,
            tenant_id=tenant_id,
        )

    async def invalidate(
        self,
        fact_id: int,
        reason: str | None = None,
        conn: aiosqlite.Connection | None = None,
        tenant_id: str = "default",
    ) -> bool:
        """Explicit severe invalidation (tombstone) + taint propagation."""
        tenant_id = self._resolve_tenant(tenant_id)

        if conn:
            return await self._invalidate_impl(conn, fact_id, reason, tenant_id)

        import typing

        async with self.session() as _raw_conn:
            _conn = typing.cast(aiosqlite.Connection, _raw_conn)
            res = await self._invalidate_impl(_conn, fact_id, reason, tenant_id)
            await _conn.commit()
            return res

    async def _invalidate_impl(
        self, conn: aiosqlite.Connection, fact_id: int, reason: str | None, tenant_id: str
    ) -> bool:
        """Delegated invalidation logic (tombstone + taint)."""
        return await invalidate_impl_logic(
            mixin_instance=self._engine,
            conn=conn,
            fact_id=fact_id,
            reason=reason,
            tenant_id=tenant_id,
        )

    async def purge(
        self,
        fact_id: int,
        tenant_id: str = "default",
        force: bool = False,
    ) -> bool:
        """Delegated purge logic (Ω₄: Bounded Demolition)."""
        tenant_id = self._resolve_tenant(tenant_id)
        return await purge_logic(
            mixin_instance=self._engine, fact_id=fact_id, tenant_id=tenant_id, force=force
        )


class StoreMixin(StoreEngine, PrivacyMixin, GhostMixin, QuarantineMixin):
    """Deprecated: Legacy Mixin class for backward compatibility support."""

    MIN_CONTENT_LENGTH = MIN_CONTENT_LENGTH
    _thermal_decay_cache: ClassVar[dict[int, int]] = {}
    _thermo_counters: ClassVar[ThermodynamicCounters] = ThermodynamicCounters()
    _agent_mode: ClassVar[AgentMode] = AgentMode.ACTIVE

    def __init__(self, engine: Any):
        super().__init__(engine)
