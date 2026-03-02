"""Storage mixin — store, update, deprecate, ghost management.

Security guards  → cortex.engine.store_guards
Validators/dedup → cortex.engine.store_validators
Quarantine       → cortex.engine.store_quarantine_mixin
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.engine.embedding_engine import embed_fact_async
from cortex.engine.fact_store_core import insert_fact_record, resolve_causality
from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.nemesis import NemesisProtocol
from cortex.engine.privacy_mixin import PrivacyMixin
from cortex.engine.store_guards import run_security_guards
from cortex.engine.store_quarantine_mixin import QuarantineMixin
from cortex.engine.store_validators import MIN_CONTENT_LENGTH, check_dedup, validate_content
from cortex.memory.temporal import now_iso

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
        kwargs = {
            "project": project,
            "content": content,
            "tenant_id": tenant_id,
            "fact_type": fact_type,
            "tags": tags,
            "confidence": confidence,
            "source": source,
            "meta": meta,
            "valid_from": valid_from,
            "commit": commit,
            "tx_id": tx_id,
        }
        if conn:
            return await self._store_impl(conn, **kwargs)

        async with self.session() as conn:
            return await self._store_impl(conn, **kwargs)

    async def _run_store_validation(
        self, conn, project, content, tenant_id, fact_type, tags, confidence, source, meta
    ) -> tuple[int | None, dict | None, str]:
        from cortex.engine.bridge_guard import BridgeGuard
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
            if (existing_id := await check_dedup(conn, tenant_id, project, content)) is not None:
                return existing_id, meta, content

        meta = self._apply_privacy_shield(content, project, meta)
        meta = run_security_guards(content, project, source, meta)

        _db_path = getattr(self, "db_path", None) or getattr(self, "_db_path", None)
        meta = resolve_causality(str(_db_path) if _db_path else None, project, meta)

        if rej := NemesisProtocol.analyze(content, db_path=str(_db_path) if _db_path else None):
            logger.warning("NEMESIS REJECTION: %s", rej)
            raise ValueError(rej)

        if fact_type == "bridge":
            bridge_res = await BridgeGuard.validate_bridge(conn, content, project, tenant_id)
            if not bridge_res["allowed"]:
                raise ValueError(f"BRIDGE BLOCKED: {bridge_res['reason']}")
            if bridge_res["meta_flags"]:
                meta = {**(meta or {}), **bridge_res["meta_flags"]}

        return None, meta, content

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
        dedupe_id, meta, content = await self._run_store_validation(
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
        )

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

        try:
            from cortex.signals.fact_hook import emit_fact_stored

            if db_p := (getattr(self, "db_path", None) or getattr(self, "_db_path", None)):
                emit_fact_stored(
                    db_path=str(db_p),
                    fact_id=fact_id,
                    project=project,
                    fact_type=fact_type,
                    source=source or "engine:store",
                    tenant_id=tenant_id,
                )
        except Exception:
            pass

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
            except Exception:
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
            query = (
                "SELECT tenant_id, project, content, fact_type, tags, confidence, source, meta "
                "FROM facts WHERE id = ? AND valid_until IS NULL"
            )
            cursor = await conn.execute(query, (fact_id,))
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
        self, fact_id: int, reason: str | None = None, conn: aiosqlite.Connection | None = None
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
            "SELECT tenant_id, project FROM facts WHERE id = ? AND valid_until IS NULL", (fact_id,)
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
        except Exception:
            pass
        await self._log_transaction(
            conn, project, "deprecate", {"fact_id": fact_id, "reason": reason}
        )

    _validate_content = staticmethod(validate_content)
    _check_dedup = staticmethod(check_dedup)
    _run_security_guards = staticmethod(run_security_guards)
