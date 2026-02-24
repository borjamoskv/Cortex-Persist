"""Storage mixin — store, update, deprecate, ghost management."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.privacy_mixin import PrivacyMixin
from cortex.memory.temporal import now_iso

__all__ = ["StoreMixin"]

logger = logging.getLogger("cortex")


class StoreMixin(PrivacyMixin, GhostMixin):
    """Sovereign Storage Layer. Handles facts lifecycle with Zero-Trust isolation."""

    MIN_CONTENT_LENGTH = 10

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
        self, conn: aiosqlite.Connection, fact_id: int, content: str
    ) -> None:
        """Generate and store embedding for a fact asynchronously."""
        if getattr(self, "_auto_embed", False) and getattr(self, "_vec_available", False):
            try:
                embedding = self._get_embedder().embed(content)
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)

    async def _process_side_effects_async(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        project: str,
        content: str,
        fact_type: str,
        ts: str,
    ) -> None:
        """Process side effects: transactions and graph extraction."""
        from cortex.graph import process_fact_graph

        try:
            await process_fact_graph(conn, fact_id, content, project, ts)
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

        new_tx_id = await self._log_transaction(
            conn, project, "store", {"fact_id": fact_id, "fact_type": fact_type}
        )
        await conn.execute("UPDATE facts SET tx_id = ? WHERE id = ?", (new_tx_id, fact_id))

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
        # ──────────────────────────────────────────────────────────
        content = self._validate_content(project, content, fact_type)

        # check for duplicates if NOT an internal update
        if not (meta and meta.get("previous_fact_id")):
            existing_id = await self._check_dedup(conn, tenant_id, project, content)
            if existing_id is not None:
                return existing_id

        meta = self._apply_privacy_shield(content, project, meta)
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()

        encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
        encrypted_meta = enc.encrypt_json(meta, tenant_id=tenant_id)

        # Wave 2: Integrity-First. Log transaction before fact storage.
        if tx_id is None:
            tx_id = await self._log_transaction(
                conn, project, "store", {"fact_type": fact_type, "status": "storing"}
            )

        from cortex.utils.canonical import compute_fact_hash

        f_hash = compute_fact_hash(content)

        # Ed25519 digital signature (optional — non-blocking)
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

        # We decoupled `facts_fts` from triggers to store plaintext metadata.
        # Now we insert FTS records manually in the application code.
        # FTS always stores plaintext for search (separate from auto_embed).
        try:
            await conn.execute(
                "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact_id, content, project, tags_json, fact_type),
            )
        except (sqlite3.Error, aiosqlite.Error) as e:
            logger.warning("Failed to update FTS for fact %d: %s", fact_id, e)

        # Pass fact_id to side effects (except tx log which is already done)
        await self._embed_fact_async(conn, fact_id, content)

        # Original process_fact_graph needs the fact_id
        from cortex.graph import process_fact_graph

        try:
            await process_fact_graph(conn, fact_id, content, project, ts)
        except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
            logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

        if commit:
            await conn.commit()

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

            # Pass conn to store to maintain transaction
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
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "WHERE id = ? AND valid_until IS NULL",
            (ts, ts, reason or "deprecated", fact_id),
        )

        # FTS5 plaintext index cleanup
        if cursor.rowcount > 0:
            try:
                await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
            except (sqlite3.Error, aiosqlite.Error) as e:
                logger.warning("Failed to remove FTS for fact %d: %s", fact_id, e)

            cursor = await conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
            row = await cursor.fetchone()
            await self._log_transaction(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Enqueue for Neo4j sync
            await conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending"),
            )
            return True
        return False

    def _validate_content(self, project: str, content: str, fact_type: str) -> str:
        """Sovereign Content Gatekeeper."""
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        content = content.strip()
        if len(content) < self.MIN_CONTENT_LENGTH:
            raise ValueError(
                f"content too short ({len(content)} chars, min {self.MIN_CONTENT_LENGTH})"
            )

        if fact_type == "decision" and content.startswith("DECISION: DECISION:"):
            content = content.replace("DECISION: DECISION:", "DECISION:", 1)

        return content

    async def _check_dedup(
        self,
        conn: aiosqlite.Connection,
        tenant_id: str,
        project: str,
        content: str,
    ) -> int | None:
        """Verify if fact already exists with Zero-G entropy penalty."""
        # Use encrypted content comparison if DB doesn't have partial indices
        # But for dedup to work with encryption, we use the same key.
        # However, AES-GCM has different nonces. So we can't compare cyphertext!
        # WE MUST CHECK PLAIN CONTENT if we want dedup.
        # But wait, 'content' in column is encrypted.
        # Option A: Vector similarity (expensive)
        # Option B: Content hash (un-salted) stored in a separate column?
        # Let's see facts table definition.
        # Schema says: hash TEXT (Wave 4: Global Integrity)
        # So we should compare by hash!

        from cortex.utils.canonical import compute_fact_hash

        f_hash = compute_fact_hash(content)

        cursor = await conn.execute(
            "SELECT id FROM facts WHERE tenant_id = ? AND project = ? AND hash = ? "
            "AND valid_until IS NULL LIMIT 1",
            (tenant_id, project, f_hash),
        )
        existing = await cursor.fetchone()
        if existing:
            return existing[0]
        return None
