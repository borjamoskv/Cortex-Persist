# [C5-REAL] Exergy-Maximized
"""Storage mixin - store, update, deprecate, ghost management.

Security guards  → cortex.engine.store_guards
Validators/dedup → cortex.engine.core.store_validators
Quarantine       → cortex.engine.core.store_quarantine_mixin
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import aiosqlite
from cortex.database.core import causal_write

from cortex.crypto import get_default_encrypter
from cortex.engine.uncategorized.capabilities import CapabilityRegistry
from cortex.engine.core.embedding_engine import embed_fact_async
from cortex.engine.core.fact_store_core import insert_fact_record
from cortex.engine.uncategorized.ghost_mixin import GhostMixin
from cortex.engine.uncategorized.privacy_mixin import PrivacyMixin
from cortex.engine.core.store_mutation import (
    deprecate_impl_logic,
    invalidate_impl_logic,
    purge_logic,
)
from cortex.engine.core.store_quarantine_mixin import QuarantineMixin
from cortex.engine.core.store_validation import run_store_validation_logic
from cortex.engine.core.store_validators import MIN_CONTENT_LENGTH, check_dedup, validate_content
from cortex.guards.thermodynamic import AgentMode, ThermodynamicCounters

# now_iso removed (internal use relocated)

__all__ = ["StoreMixin"]

logger = logging.getLogger("cortex")


class StoreMixin(PrivacyMixin, GhostMixin, QuarantineMixin):
    """Sovereign Storage Layer - Fact Lifecycle with Zero-Trust Isolation.

    Inherits from ``PrivacyMixin``, ``GhostMixin``, ``QuarantineMixin``
    (all of which inherit from ``EngineMixinBase``), providing:
    - ``store()``: Single-fact persistence with dedup + guards.
    - ``store_many()``: Batch persistence (M facts in 1 transaction).
    - ``update()``: Temporal versioning (deprecate → replace).
    - ``deprecate()``: Soft-delete with audit trail.
    """

    store_fact = None  # Placeholder for alias
    MIN_CONTENT_LENGTH = MIN_CONTENT_LENGTH
    _thermal_decay_cache: ClassVar[dict[int, int]] = {}
    _thermo_counters: ClassVar[ThermodynamicCounters] = ThermodynamicCounters()
    _agent_mode: ClassVar[AgentMode] = AgentMode.ACTIVE

    async def store(
        self,
        project: str,
        content: str,
        tenant_id: str = "default",
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        actor_id: str | None = None,
        meta: dict[str, Any] | None = None,
        valid_from: str | None = None,
        commit: bool = True,
        tx_id: int | None = None,
        parent_decision_id: int | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """Store a new fact with proper connection management."""
        tenant_id = self._resolve_tenant(tenant_id)
        if source is None and actor_id:
            source = (
                actor_id
                if actor_id.startswith(("agent:", "cli", "api", "human"))
                else f"agent:{actor_id}"
            )

        # ═══ SOVEREIGN LOCK (Axiom Ω_CB) ═══
        if getattr(self, "system_state", "ACTIVE") == "LOCKED_EPISTEMIC_HALT":
            if source != "daemon:circuit-breaker":
                raise RuntimeError(
                    "CORTEX Engine is in LOCKED_EPISTEMIC_HALT state due to cognitive thrashing. "
                    "Write access denied until Sovereign Lock is lifted by Autodidact-Omega."
                )

        if conn:
            started_tx = False
            if not conn.in_transaction:
                await conn.execute("BEGIN IMMEDIATE")
                started_tx = True
            try:
                return await self._store_impl(
                    conn,
                    project=project,
                    content=content,
                    tenant_id=tenant_id,
                    fact_type=fact_type,
                    tags=tags,
                    confidence=confidence,
                    source=source,
                    actor_id=actor_id,
                    meta=meta,
                    valid_from=valid_from,
                    commit=commit,
                    tx_id=tx_id,
                    parent_decision_id=parent_decision_id,
                )
            except Exception:
                if started_tx and conn.in_transaction:
                    await conn.rollback()
                raise

        async with self.session() as _conn:
            started_tx = False
            if not _conn.in_transaction:
                await _conn.execute("BEGIN IMMEDIATE")
                started_tx = True
            try:
                return await self._store_impl(
                    _conn,
                    project=project,
                    content=content,
                    tenant_id=tenant_id,
                    fact_type=fact_type,
                    tags=tags,
                    confidence=confidence,
                    source=source,
                    actor_id=actor_id,
                    meta=meta,
                    valid_from=valid_from,
                    commit=commit,
                    tx_id=tx_id,
                    parent_decision_id=parent_decision_id,
                )
            except Exception:
                if started_tx and _conn.in_transaction:
                    await _conn.rollback()
                raise

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
            mixin_instance=self,
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
        actor_id: str | None,
        meta: dict[str, Any] | None,
        valid_from: str | None,
        commit: bool,
        tx_id: int | None,
        parent_decision_id: int | None = None,
    ) -> int:
        meta = meta or {}
        if "cortex_taint" not in meta:
            import time
            meta["cortex_taint"] = f"taint:system:internal:{time.time()}:0:system_bypass"

        await self._run_pre_store_guards(conn, content, project, fact_type, meta, tenant_id)

        from cortex.guards.ctre_guard import CTRECollisionError

        try:
            dedupe_id, meta, content, fact_type = await self._run_store_validation(
                conn, project, content, tenant_id, fact_type, tags, confidence, source, meta
            )
        except CTRECollisionError as e:
            # Emit cryptographic audit trail for the SAGA abort
            await self._log_transaction(
                conn,
                project,
                "saga_abort",
                {
                    "reason": "TOCTOU_COLLISION",
                    "epsilon_us": e.epsilon,
                    "expected_hash": e.expected_hash,
                    "current_hash": e.current_hash,
                },
                tenant_id=tenant_id,
            )
            # Propagate to the agent so it knows it must retry the perception loop
            raise

        if dedupe_id is not None:
            return dedupe_id

        with causal_write(conn):
            tx_id = await self._resolve_tx_id(tx_id, conn, project, content, fact_type, tenant_id, actor_id=actor_id)
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
                taint_already_verified=True,
            )

            await self._run_post_store_tasks(
                conn, fact_id, project, content, fact_type, tags, source, tenant_id
            )

        self._invalidate_l1_cache(tenant_id)

        if commit:
            await conn.commit()

        return fact_id

    async def _run_pre_store_guards(
        self,
        conn: aiosqlite.Connection,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any] | None,
        tenant_id: str,
    ) -> None:
        pipeline = getattr(self, "_guard_pipeline", None)
        if pipeline is not None:
            await pipeline.run_guards(
                content, project, fact_type, meta or {}, conn, tenant_id=tenant_id
            )

    async def _resolve_tx_id(
        self,
        tx_id: int | None,
        conn: aiosqlite.Connection,
        project: str,
        content: str,
        fact_type: str,
        tenant_id: str,
        actor_id: str | None = None,
    ) -> int:
        if tx_id is not None:
            return tx_id
        from cortex.utils.canonical import compute_fact_hash

        content_hash = compute_fact_hash(content)
        return await self._log_transaction(
            conn,
            project,
            "store",
            {"fact_type": fact_type, "content_hash": content_hash, "actor_id": actor_id or "system"},
            tenant_id=tenant_id,  # pyright: ignore
        )

    async def _run_post_store_tasks(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        project: str,
        content: str,
        fact_type: str,
        tags: list[str] | None,
        source: str | None,
        tenant_id: str,
    ) -> None:
        caps = CapabilityRegistry.get_instance().capabilities
        if (
            getattr(self, "_auto_embed", False)
            and getattr(self, "_vec_available", False)
            and caps.embeddings
        ):
            await embed_fact_async(
                conn,
                fact_id,
                project,
                content,
                self._get_embedder(),
                getattr(self, "_memory_manager", None),
                tenant_id,
            )

        if hasattr(self, "right_brain") and self.right_brain is not None:  # pyright: ignore
            self.right_brain.ingest_ambient_signal(  # pyright: ignore
                {
                    "source": source or "unknown",
                    "fact_type": fact_type,
                    "project": project,
                    "tags": tags or [],
                }
            )

        pipeline = getattr(self, "_guard_pipeline", None)
        if pipeline is not None:
            db_path = str(getattr(self, "_db_path", "") or "")
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
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as _ph_err:  # noqa: BLE001
                logger.debug("[AX-II] GuardPipeline post-hooks skipped: %s", _ph_err)

    async def store_many(self, facts: list[dict[str, Any]]) -> list[int]:
        if not facts:
            raise ValueError("facts list cannot be empty")
        async with self.session() as conn:
            if not conn.in_transaction:
                await conn.execute("BEGIN IMMEDIATE")
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
            with causal_write(conn):
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

    def _invalidate_l1_cache(self, tenant_id: str) -> None:
        """Invalidate search L1 cache for the tenant."""
        try:
            from cortex.cache import RedisL1Cache

            cache = RedisL1Cache.singleton()
            if cache.available:
                cache.flush_namespace(f"search:{tenant_id}")
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            logger.debug("[L1 Cache] Invalidation failed: %s", exc)

    async def _deprecate_impl(
        self, conn: aiosqlite.Connection, fact_id: int, reason: str | None, tenant_id: str
    ) -> bool:
        """Delegated deprecation logic."""
        with causal_write(conn):
            res = await deprecate_impl_logic(
                mixin_instance=self, conn=conn, fact_id=fact_id, reason=reason, tenant_id=tenant_id
            )
        if res:
            self._invalidate_l1_cache(tenant_id)
        return res

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
        with causal_write(conn):
            res = await invalidate_impl_logic(
                mixin_instance=self, conn=conn, fact_id=fact_id, reason=reason, tenant_id=tenant_id
            )
        if res:
            self._invalidate_l1_cache(tenant_id)
        return res

    async def purge(
        self,
        fact_id: int,
        tenant_id: str = "default",
        force: bool = False,
    ) -> bool:
        """Delegated purge logic (Ω₄: Bounded Demolition)."""
        tenant_id = self._resolve_tenant(tenant_id)
        res = await purge_logic(
            mixin_instance=self, fact_id=fact_id, tenant_id=tenant_id, force=force
        )
        if res:
            self._invalidate_l1_cache(tenant_id)
        return res

    _validate_content = staticmethod(validate_content)
    _check_dedup = staticmethod(check_dedup)
