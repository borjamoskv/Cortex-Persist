"""Storage mixin — store, update, deprecate, ghost management.

Security guards  → cortex.engine.store_guards
Validators/dedup → cortex.engine.store_validators
Quarantine       → cortex.engine.store_quarantine_mixin
"""

from __future__ import annotations

import json
import logging
from typing import Any, ClassVar

import aiosqlite

# Hoisted from _run_store_validation hot path
from cortex.engine.bridge_guard import BridgeGuard
from cortex.engine.embedding_engine import embed_fact_async
from cortex.engine.fact_store_core import (
    insert_fact_record,
    resolve_causality_async,
)
from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.membrane.sanitizer import SovereignSanitizer
from cortex.engine.nemesis import NemesisProtocol
from cortex.engine.privacy_mixin import PrivacyMixin
from cortex.engine.storage_guard import StorageGuard
from cortex.engine.store_guards import run_security_guards
from cortex.engine.store_quarantine_mixin import QuarantineMixin
from cortex.engine.store_validators import MIN_CONTENT_LENGTH, check_dedup, validate_content
from cortex.memory.temporal import now_iso

__all__ = ["StoreMixin"]

logger = logging.getLogger("cortex")


class StoreMixin(PrivacyMixin, GhostMixin, QuarantineMixin):
    """Sovereign Storage Layer — Fact Lifecycle with Zero-Trust Isolation.

    Inherits from ``PrivacyMixin``, ``GhostMixin``, ``QuarantineMixin``
    (all of which inherit from ``EngineMixinBase``), providing:
    - ``store()``: Single-fact persistence with dedup + guards.
    - ``store_many()``: Batch persistence (M facts in 1 transaction).
    - ``update()``: Temporal versioning (deprecate → replace).
    - ``deprecate()``: Soft-delete with audit trail.
    """

    MIN_CONTENT_LENGTH = MIN_CONTENT_LENGTH
    _thermal_decay_cache: ClassVar[dict[int, int]] = {}

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
        conn: aiosqlite.Connection | None = None,
        parent_decision_id: int | None = None,
    ) -> int:
        """Store a new fact with proper connection management."""
        tenant_id = self._resolve_tenant(tenant_id)

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
        self, conn, project, content, tenant_id, fact_type, tags, confidence, source, meta
    ) -> tuple[int | None, dict | None, str, str]:
        StorageGuard.validate(
            project=project,
            content=content,
            fact_type=fact_type,
            source=source,
            confidence=confidence,
            tags=tags,
            meta=meta,
        )
        content = validate_content(project, content, fact_type)

        if not (meta and meta.get("previous_fact_id")):
            # 1. Exact Structural Hash Dedup (O(1))
            if (existing_id := await check_dedup(conn, tenant_id, project, content)) is not None:
                return existing_id, meta, content, fact_type

            # 2. Semantic Deduplication (O(N) Vector Search) - V8 Data Governance
            manager = getattr(self, "_memory_manager", None)
            if manager is not None and getattr(manager, "_l2", None) is not None:
                try:
                    # L2 recall handles decay, success_rate and cosine similarity natively
                    similar_facts = await manager._l2.recall(
                        query=content,
                        limit=1,
                        project=project,
                        tenant_id=tenant_id,
                    )
                    if similar_facts:
                        top_match = similar_facts[0]
                        score = getattr(top_match, "_recall_score", 0.0)
                        # Threshold > 0.92 means extreme similarity (almost identical meaning)
                        if score > 0.92:
                            logger.info(
                                "🛡️ [V8 Governance] Semantic deduplication blocked insert "
                                "(Score: %.3f). ID: %s",
                                score,
                                top_match.id,
                            )
                            try:
                                fact_id_int = int(top_match.id)

                                # Axiom Ω7: Defensive Mutation (Thermal Decay Quarantine)
                                hits = self.__class__._thermal_decay_cache.get(fact_id_int, 0) + 1
                                self.__class__._thermal_decay_cache[fact_id_int] = hits

                                if hits > 4:
                                    logger.warning(
                                        "☣️ [THERMAL DECAY] Fact %d reached critical entropy "
                                        "(%d hits). Quarantining.",
                                        fact_id_int,
                                        hits,
                                    )
                                    # Archive the decaying abstraction before it processes further
                                    await self.deprecate(
                                        fact_id=fact_id_int,
                                        reason=f"Thermal decay quarantine (Semantic loop {hits}x)",
                                        conn=conn,
                                        tenant_id=tenant_id,
                                    )
                                    self.__class__._thermal_decay_cache[fact_id_int] = 0
                                else:
                                    await conn.execute(
                                        "UPDATE facts SET last_accessed = CURRENT_TIMESTAMP "
                                        "WHERE id = ?",
                                        (fact_id_int,),
                                    )
                                return fact_id_int, meta, content, fact_type
                            except (ValueError, TypeError):
                                logger.warning(
                                    "Non-integer ID returned from vector store. Skipping dedup."
                                )
                except (RuntimeError, ValueError, TypeError, OSError) as e:
                    logger.debug("Semantic deduplication skipped due to internal error: %s", e)
        meta = self._apply_privacy_shield(content, project, meta)
        meta = run_security_guards(content, project, source, meta)

        # Omega-3: Byzantine Default - Pass through SovereignSanitizer

        raw_engram = {
            "type": fact_type,
            "source": source or "engine:store",
            "topic": project,
            "content": content,
            "metadata": meta or {},
        }
        pure_engram, membrane_log = SovereignSanitizer.digest(raw_engram)
        content = pure_engram.content
        meta = pure_engram.metadata
        if hasattr(membrane_log, "model_dump"):
            meta["_membrane_log"] = membrane_log.model_dump()
        else:
            meta["_membrane_log"] = membrane_log.dict()  # Fallback for V1 if needed

        meta = await resolve_causality_async(conn, project, meta)

        # Ω₆: Nemesis Analysis must be async to prevent loop starvation
        # Skip nemesis for errors and ghosts as stack traces/records might contain anti-patterns
        if fact_type not in ("error", "ghost"):
            if rej := await NemesisProtocol.analyze_async(content, conn=conn):
                logger.warning("NEMESIS REJECTION: %s", rej)
                raise ValueError(rej)

        # Ω₁: Bridge Elevation — Prescriptive pattern elevation for cross-project duplicates
        if fact_type in ("knowledge", "decision", "rule", "ghost"):
            # Don't bridge if it's an update (has previous_fact_id)
            if not (meta and meta.get("previous_fact_id")):
                source_proj = await BridgeGuard.detect_bridge_candidate(
                    conn, content, project, tenant_id
                )
                if source_proj:
                    logger.info(
                        "🌉 [Ω₁] Elevating pattern to BRIDGE: %s → %s", source_proj, project
                    )
                    fact_type = "bridge"
                    # Prescriptive pattern adoption: ensure bridge content follows BridgeGuard format
                    if "→" not in content and "->" not in content:
                        content = f"Pattern from {source_proj} → {project}. Adaptation: {content}"

        if fact_type == "bridge":
            bridge_res = await BridgeGuard.validate_bridge(conn, content, project, tenant_id)
            if not bridge_res["allowed"]:
                raise ValueError(f"BRIDGE BLOCKED: {bridge_res['reason']}")
            if bridge_res["meta_flags"]:
                meta = {**(meta or {}), **bridge_res["meta_flags"]}

        return None, meta, content, fact_type

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
        # ═══ AX-033: Pre-store guards via GuardPipeline ═══
        pipeline = getattr(self, "_guard_pipeline", None)
        if pipeline is not None:
            try:
                await pipeline.run_guards(
                    content, project, fact_type, meta or {}, conn, tenant_id=tenant_id
                )
            except ValueError:
                raise  # Guard rejections must propagate
            except Exception as _gp_err:  # noqa: BLE001
                logger.debug("[AX-033] GuardPipeline pre-store skipped: %s", _gp_err)

        dedupe_id, meta, content, fact_type = await self._run_store_validation(
            conn, project, content, tenant_id, fact_type, tags, confidence, source, meta
        )
        if dedupe_id is not None:
            return dedupe_id

        tx_id = (
            tx_id
            if tx_id is not None
            else await self._log_transaction(conn, project, "store", {"fact_type": fact_type})
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

        # ─── Dual-Write Bridge: sync parent_decision_id to facts_meta ───
        try:
            cursor = await conn.execute(
                "SELECT parent_decision_id FROM facts WHERE id = ?",
                (fact_id,),
            )
            row = await cursor.fetchone()
            resolved_parent = row[0] if row else None
            if resolved_parent is not None:
                await conn.execute(
                    "UPDATE facts_meta SET parent_decision_id = ? WHERE id = ?",
                    (str(resolved_parent), fact_id),
                )
        except (aiosqlite.Error, OSError):
            pass

        if getattr(self, "_auto_embed", False) and getattr(self, "_vec_available", False):
            await embed_fact_async(
                conn,
                fact_id,
                project,
                content,
                self._get_embedder(),
                getattr(self, "_memory_manager", None),
                tenant_id,
            )

        if commit:
            await conn.commit()

        # ═══ AX-033: Post-store hooks via GuardPipeline ═══
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
            except Exception as _ph_err:  # noqa: BLE001
                logger.debug("[AX-033] GuardPipeline post-hooks skipped: %s", _ph_err)

        # ═══ DOUBT-Ω: Post-store metacognitive evaluation (non-blocking) ═══
        try:
            from cortex.engine.metacognition import DoubtCircuit

            doubt = DoubtCircuit(conn)
            alerts = await doubt.scan_coherence_traps(project=project, tenant_id=tenant_id, limit=5)
            for alert in alerts:
                if alert.alert_type == "COHERENCE_TRAP":
                    logger.warning(
                        "🧠 [DOUBT-Ω] Coherence trap detected in project '%s': %s",
                        project,
                        alert.description,
                    )
        except Exception as _doubt_err:  # noqa: BLE001
            # Non-blocking: DoubtCircuit failure must never gate storage
            logger.debug("[DOUBT-Ω] Metacognition skipped: %s", _doubt_err)

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
                "SELECT tenant_id, project, content, fact_type, tags, "
                "confidence, source, meta "
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
                old_tags_json,
                confidence,
                source,
                raw_old_meta_json,
            ) = row
            from cortex.crypto import get_default_encrypter

            enc = get_default_encrypter()
            old_content = (
                enc.decrypt_str(raw_old_content, tenant_id=db_tenant_id) if raw_old_content else ""
            )
            new_meta = (
                enc.decrypt_json(raw_old_meta_json, tenant_id=db_tenant_id)
                if raw_old_meta_json
                else {}
            )
            if new_meta is None:
                new_meta = {}
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
                tags=tags if tags is not None else json.loads(old_tags_json),
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
    ) -> bool:  # type: ignore[reportReturnType]
        from cortex.engine.mutation_engine import MUTATION_ENGINE

        ts = now_iso()
        async with conn.execute(
            "SELECT tenant_id, project FROM facts "
            "WHERE id = ? AND tenant_id = ? AND is_tombstoned = 0",
            (fact_id, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        db_tenant_id, project = row[0], row[1]
        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fact_id,
            tenant_id=db_tenant_id,
            event_type="deprecate",
            payload={"reason": reason or "deprecated", "timestamp": ts},
            signer="store_mixin:deprecate",
            commit=False,
        )

        from cortex.engine.causality import AsyncCausalGraph

        graph = AsyncCausalGraph(conn)
        await graph.propagate_taint(fact_id=fact_id, tenant_id=db_tenant_id)

        try:
            await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        except aiosqlite.Error as _fts_err:  # FTS table may not exist in all deployments
            logger.debug("[STORE] FTS cleanup skipped for fact %d: %s", fact_id, _fts_err)
        await self._log_transaction(
            conn, project, "deprecate", {"fact_id": fact_id, "reason": reason}
        )
        return True

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
        from cortex.engine.mutation_engine import MUTATION_ENGINE

        ts = now_iso()
        async with conn.execute(
            "SELECT tenant_id, project FROM facts "
            "WHERE id = ? AND tenant_id = ? AND is_tombstoned = 0",
            (fact_id, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False

        db_tenant_id, project = row[0], row[1]

        # 1. Mutate as tombstone (most severe invalidation)
        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fact_id,
            tenant_id=db_tenant_id,
            event_type="tombstone",
            payload={"reason": reason or "invalidated", "timestamp": ts},
            signer="store_mixin:invalidate",
            commit=False,
        )

        # 2. Hard set confidence to C1 for the source fact explicitly via MutationEngine
        # Actually it's cleaner to just update it here for immediacy of the projection,
        # but in CORTEX a score_update mutation is best so it's recorded on the ledger.
        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fact_id,
            tenant_id=db_tenant_id,
            event_type="score_update",
            payload={"confidence": "C1", "consensus_score": 0.0},
            signer="store_mixin:invalidate:force",
            commit=False,
        )

        # 3. Propagate taint downward
        from cortex.engine.causality import AsyncCausalGraph

        graph = AsyncCausalGraph(conn)
        await graph.propagate_taint(fact_id=fact_id, tenant_id=db_tenant_id)

        try:
            await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        except aiosqlite.Error as _fts_err:
            logger.debug("[STORE] FTS cleanup skipped for fact %d: %s", fact_id, _fts_err)

        await self._log_transaction(
            conn, project, "invalidate", {"fact_id": fact_id, "reason": reason}
        )
        return True

    _validate_content = staticmethod(validate_content)
    _check_dedup = staticmethod(check_dedup)
    _run_security_guards = staticmethod(run_security_guards)
