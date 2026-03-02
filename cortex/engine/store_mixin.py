"""Storage mixin — store, update, deprecate, ghost management.

Security guards  → cortex.engine.store_guards
Validators/dedup → cortex.engine.store_validators
Quarantine       → cortex.engine.store_quarantine_mixin
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.privacy_mixin import PrivacyMixin
from cortex.engine.store_guards import run_security_guards
from cortex.engine.store_quarantine_mixin import QuarantineMixin
from cortex.engine.store_validators import MIN_CONTENT_LENGTH, check_dedup, validate_content
from cortex.engine.nemesis import NemesisProtocol
from cortex.memory.temporal import now_iso
from cortex.engine.causality import CausalOracle, link_causality

__all__ = ["StoreMixin"]

logger = logging.getLogger("cortex")


class StoreMixin(PrivacyMixin, GhostMixin, QuarantineMixin):
    """Sovereign Storage Layer. Handles facts lifecycle with Zero-Trust isolation."""

    MIN_CONTENT_LENGTH = MIN_CONTENT_LENGTH

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
    ) -> int:
        """Store a new fact with proper connection management."""
        if conn:
            return await self._store_impl(
                conn,
                project,
                content,
                tenant_id,
                fact_type,
                tags,
                confidence,
                source,
                meta,
                valid_from,
                commit,
                tx_id,
            )

        async with self.session() as conn:
            return await self._store_impl(
                conn,
                project,
                content,
                tenant_id,
                fact_type,
                tags,
                confidence,
                source,
                meta,
                valid_from,
                commit,
                tx_id,
            )

    async def _embed_fact_async(
        self, conn: aiosqlite.Connection, fact_id: int, project: str, content: str
    ) -> None:
        """Generate and store embedding for a fact asynchronously.

        Now supports G10 Specular Memory (HDC-Native).
        """
        # 1. Legacy Vector Store (L2 Dense)
        if getattr(self, "_auto_embed", False) and getattr(self, "_vec_available", False):
            try:
                embedding = self._get_embedder().embed(content)
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)

        # 2. Vector Alpha (G10 Specular Memory)
        mm = getattr(self, "_memory_manager", None)
        if mm and hasattr(mm, "get_context_vector") and mm._hdc_encoder:
            try:
                import numpy as np

                from cortex.memory.hdc.algebra import bind
                from cortex.memory.models import CortexFactModel

                fact_hv = mm._hdc_encoder.encode_text(content)
                context_hv = mm.get_context_vector()

                if context_hv is not None:
                    intent_hv = bind(fact_hv, context_hv)
                    specular_bytes = np.array(intent_hv, dtype=np.float32).tobytes()
                    await conn.execute(
                        "INSERT INTO specular_embeddings (fact_id, embedding) VALUES (?, ?)",
                        (fact_id, specular_bytes),
                    )
                    logger.debug("Specular Memory indexed for fact %d", fact_id)

                    if mm._hdc:
                        fact = CortexFactModel(
                            id=str(fact_id),
                            tenant_id=getattr(self, "_tenant_id", "default"),
                            project_id=project,
                            content=content,
                            embedding=fact_hv.tolist(),
                            specular_embedding=intent_hv.tolist(),
                        )
                        await mm._hdc.memorize(fact)
                        logger.debug("Vector Alpha (HDC) indexed for fact %d", fact_id)
            except (
                sqlite3.Error,
                aiosqlite.Error,
                OSError,
                ValueError,
                AttributeError,
                TypeError,
            ) as e:
                logger.warning("Specular Memory indexing failed for fact %d: %s", fact_id, e)

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
    ) -> int:
        # ── Leap 1 Guard: Mandatory pre-store validation ──────────
        from cortex.engine.storage_guard import StorageGuard

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
            existing_id = await check_dedup(conn, tenant_id, project, content)
            if existing_id is not None:
                return existing_id

        meta = self._apply_privacy_shield(content, project, meta)
        meta = run_security_guards(content, project, source, meta)

        # ── Causal Linking (Ω₁) ───────────────────────────────────
        # Automatically detect the 'why' behind this store
        _db_path = getattr(self, "db_path", None) or getattr(self, "_db_path", None)
        if _db_path and not (meta and meta.get("causal_parent")):
            parent_sig = CausalOracle.find_parent_signal(str(_db_path), project)
            meta = link_causality(meta, parent_sig)

        # ── Nemesis Immunological Guard ───────────────────────────
        rejection_reason = NemesisProtocol.analyze(
            content, db_path=str(_db_path) if _db_path else None
        )
        if rejection_reason:
            logger.warning("NEMESIS REJECTION: %s", rejection_reason)
            # Ω₅: The error is the fuel. Raise now to trigger immediate reflex.
            raise ValueError(rejection_reason)

        # ── Bridge Validation Guard ───────────────────────────────
        if fact_type == "bridge":
            from cortex.engine.bridge_guard import BridgeGuard

            bridge_result = await BridgeGuard.validate_bridge(conn, content, project, tenant_id)
            if not bridge_result["allowed"]:
                raise ValueError(f"BRIDGE BLOCKED: {bridge_result['reason']}")
            if bridge_result["meta_flags"]:
                meta = {**(meta or {}), **bridge_result["meta_flags"]}

        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()
        encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
        encrypted_meta = enc.encrypt_json(meta, tenant_id=tenant_id)

        if tx_id is None:
            tx_id = await self._log_transaction(
                conn, project, "store", {"fact_type": fact_type, "status": "storing"}
            )

        from cortex.utils.canonical import compute_fact_hash

        f_hash = compute_fact_hash(content)

        sig_b64: str | None = None
        pub_b64: str | None = None
        try:
            from cortex.security.signatures import get_default_signer

            signer = get_default_signer()
            if signer and signer.can_sign:
                sig_b64 = signer.sign(content, f_hash)
                pub_b64 = signer.public_key_b64
        except (ImportError, ValueError, OSError) as e:
            logger.debug("Fact signing skipped: %s", e)

        cursor = await conn.execute(
            "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, hash, signature, signer_pubkey, "
            "created_at, updated_at, tx_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                project,
                encrypted_content,
                fact_type,
                tags_json,
                confidence,
                ts,
                source,
                encrypted_meta,
                f_hash,
                sig_b64,
                pub_b64,
                ts,
                ts,
                tx_id,
            ),
        )
        fact_id = cursor.lastrowid

        try:
            await conn.execute(
                "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact_id, content, project, tags_json, fact_type),
            )
        except (sqlite3.Error, aiosqlite.Error) as e:
            logger.warning("Failed to update FTS for fact %d: %s", fact_id, e)

        await self._embed_fact_async(conn, fact_id, project, content)

        from cortex.graph import process_fact_graph

        try:
            await process_fact_graph(conn, fact_id, content, project, ts)
        except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
            logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

        if commit:
            await conn.commit()

        try:
            from cortex.signals.fact_hook import emit_fact_stored

            _db_path = getattr(self, "db_path", None) or getattr(self, "_db_path", None)
            if _db_path:
                emit_fact_stored(
                    db_path=str(_db_path),
                    fact_id=fact_id,
                    project=project,
                    fact_type=fact_type,
                    source=source or "engine:store",
                    tenant_id=tenant_id,
                )
        except Exception:  # noqa: BLE001 — hook must never break store
            pass

        return fact_id

    async def store_many(self, facts: list[dict[str, Any]]) -> list[int]:
        if not facts:
            raise ValueError("facts list cannot be empty")

        async with self.session() as conn:
            ids = []
            try:
                for fact in facts:
                    if "project" not in fact:
                        raise ValueError("project cannot be empty")
                    if "content" not in fact:
                        raise ValueError("content cannot be empty")
                    ids.append(await self.store(commit=False, conn=conn, **fact))
                await conn.commit()
                return ids
            except (sqlite3.Error, OSError, ValueError):
                await conn.rollback()
                raise

    async def update(
        self,
        fact_id: int,
        content: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> int:
        async with self.session() as conn:
            cursor = await conn.execute(
                "SELECT tenant_id, project, content, fact_type, tags, confidence, source, meta "
                "FROM facts WHERE id = ? AND valid_until IS NULL",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Fact {fact_id} not found")

            (
                tenant_id,
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
                enc.decrypt_str(raw_old_content, tenant_id=tenant_id) if raw_old_content else ""
            )
            new_meta = (
                enc.decrypt_json(raw_old_meta_json, tenant_id=tenant_id)
                if raw_old_meta_json
                else {}
            )
            if meta:
                new_meta.update(meta)
            new_meta["previous_fact_id"] = fact_id

            new_id = await self.store(
                project=project,
                content=content if content is not None else old_content,
                tenant_id=tenant_id,
                fact_type=fact_type,
                tags=tags if tags is not None else json.loads(old_tags_json),
                confidence=confidence,
                source=source,
                meta=new_meta,
                conn=conn,
                commit=False,
            )
            await self.deprecate(fact_id, reason=f"updated_by_{new_id}", conn=conn)
            await conn.commit()
            return new_id

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        if conn:
            return await self._deprecate_impl(conn, fact_id, reason)

        async with self.session() as conn:
            res = await self._deprecate_impl(conn, fact_id, reason)
            await conn.commit()
            return res

    async def _deprecate_impl(
        self, conn: aiosqlite.Connection, fact_id: int, reason: str | None
    ) -> bool:
        from cortex.engine.mutation_engine import MUTATION_ENGINE

        ts = now_iso()
        cursor = await conn.execute(
            "SELECT tenant_id, project FROM facts WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        tenant_id, project = row[0], row[1]
        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fact_id,
            tenant_id=tenant_id,
            event_type="deprecate",
            payload={"reason": reason or "deprecated", "timestamp": ts},
            signer="store_mixin:deprecate",
            commit=False,
        )

        try:
            await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        except (sqlite3.Error, aiosqlite.Error) as e:
            logger.warning("Failed to remove FTS for fact %d: %s", fact_id, e)

        await self._log_transaction(
            conn, project, "deprecate", {"fact_id": fact_id, "reason": reason}
        )
        return True

    # Delegates: validate_content / _check_dedup → store_validators (pure functions)
    _validate_content = staticmethod(validate_content)
    _check_dedup = staticmethod(check_dedup)

    # Delegates: security guards → store_guards (pure functions)
    _run_security_guards = staticmethod(run_security_guards)
