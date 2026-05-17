"""CORTEX v5.2 — Solid-State Mutation Engine (CQRS Write Gateway).
The ONLY sanctioned write path for fact state changes. Every mutation is:
1. Appended to `entity_events` (immutable, hash-chained, schema-free payload)
2. Projected into `facts` (mutable materialized view for O(1) reads)
Both operations execute inside a single atomic SQLite transaction.
Axiom: No application code may execute `UPDATE facts` for state changes
directly. All state transitions flow through `FactMutationEngine.apply()`.
Design principles:
- entity_events.event_type is a free string: the agent defines the taxonomy,
  the substrate stores it. MOSKV-N can invent new event types without migrations.
- entity_events.payload is free-form JSON: the agent defines the structure,
  the substrate persists it.
- entity_events.schema_version tracks payload format evolution per-row, not
  per-table. No global migrations needed for new payload shapes.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.causality import AsyncCausalGraph
from cortex.extensions.axioms.topological_id import flake_gen

__all__ = ["FactMutationEngine"]
logger = logging.getLogger("cortex.mutation_engine")
# Current payload schema version written by MOSKV-1.
_PAYLOAD_SCHEMA_VERSION = "1"
_FACT_COLUMNS_CACHE: dict[int, set[str]] = {}
_ROLLBACK_ERRORS = (
    aiosqlite.Error,
    AssertionError,
    KeyError,
    LookupError,
    PermissionError,
    RuntimeError,
    TypeError,
    ValueError,
)
class FactMutationEngine:
    """Solid-State Write Gateway for CORTEX facts.
    Usage::
        engine = FactMutationEngine()
        await engine.apply(
            conn,
            fact_id=42,
            tenant_id="default",
            event_type="score_update",
            payload={"consensus_score": 0.85, "confidence": "verified"},
            signer="consensus_mixin",
        )
    The method atomically:
    1. INSERTs a hash-chained row into ``entity_events``.
    2. Projects the mutation into ``facts`` via an UPDATE.
    If the projection fails, the entire transaction rolls back —
    ``entity_events`` and ``facts`` stay perfectly in sync.
    """
    # ── Core API ─────────────────────────────────────────────────────
    async def apply(
        self,
        conn: aiosqlite.Connection,
        *,
        fact_id: int,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        signer: str = "",
        commit: bool = True,
    ) -> str:
        """Append an immutable event and project its effect atomically.
        Args:
            conn: Active aiosqlite connection.
            fact_id: The entity (fact) being mutated.
            tenant_id: Zero-Trust tenant isolation.
            event_type: Free string — agent-defined taxonomy.
            payload: Free-form JSON — agent-defined structure.
            signer: Who wrote this event (agent name, system, human).
            commit: Whether to commit the transaction (False for batched ops).
        Returns:
            The UUID of the newly created event.
        """
        event_id = flake_gen.next_lexicographic_id()
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        # ── 1. Hash-chain: link to the last event for this entity ────
        prev_hash = await self._get_last_hash(conn, fact_id)
        chain_input = f"{event_id}:{fact_id}:{tenant_id}:{event_type}:{payload_str}:{prev_hash}"
        signature = hashlib.sha3_256(chain_input.encode()).hexdigest()
        # ── 2. Atomic transaction: INSERT event + UPDATE projection ──
        try:
            await conn.execute(
                "INSERT INTO entity_events "
                "(id, entity_id, tenant_id, event_type, payload, "
                "timestamp, prev_hash, signature, signer, schema_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    fact_id,
                    tenant_id,
                    event_type,
                    payload_str,
                    ts,
                    prev_hash,
                    signature,
                    signer,
                    _PAYLOAD_SCHEMA_VERSION,
                ),
            )
            # ── 3. Project mutation into facts (materialized view) ───────
            await self._project(conn, fact_id, tenant_id, event_type, payload)
            if commit:
                await conn.commit()
        except _ROLLBACK_ERRORS:
            await conn.rollback()
            raise
        logger.debug(
            "Solid-state event %s: entity=%d type=%s signer=%s",
            event_id,
            fact_id,
            event_type,
            signer,
        )
        return event_id
    # ── Hash-Chain ───────────────────────────────────────────────────
    async def _get_last_hash(
        self,
        conn: aiosqlite.Connection,
        entity_id: int,
    ) -> str:
        """Fetch the signature of the most recent event for this entity."""
        async with conn.execute(
            "SELECT signature FROM entity_events WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
            (entity_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else "GENESIS"
    async def _get_fact_tenant_id(self, conn: aiosqlite.Connection, fact_id: int) -> str:
        """Resolve the tenant_id for a fact from the materialized view."""
        async with conn.execute("SELECT tenant_id FROM facts WHERE id = ?", (fact_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row and row[0] else "default"
    async def _facts_columns(self, conn: aiosqlite.Connection) -> set[str]:
        """Return the facts schema columns for the current connection."""
        cache_key = id(conn)
        cached = _FACT_COLUMNS_CACHE.get(cache_key)
        if cached is not None:
            return cached
        async with conn.execute("PRAGMA table_info(facts)") as cursor:
            rows = await cursor.fetchall()
        columns = {str(row[1]) for row in rows}
        _FACT_COLUMNS_CACHE[cache_key] = columns
        return columns
    async def _metadata_column(self, conn: aiosqlite.Connection) -> str | None:
        """Resolve the metadata column name across legacy schemas."""
        columns = await self._facts_columns(conn)
        if "metadata" in columns:
            return "metadata"
        if "meta" in columns:
            return "meta"
        return None
    # ── Projection Layer (MOSKV-1 specific) ──────────────────────────
    async def _project(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Update the facts materialized view based on event type.
        This is the ONLY place where ``UPDATE facts`` is allowed.
        The projection is agent-specific (MOSKV-1 knows what fields
        to update). Future MOSKV-N versions can override or extend.
        """
        _PROJECTORS: dict[str, Any] = {
            "deprecate": self._proj_deprecate,
            "tombstone": self._proj_tombstone,
            "archaeology_merge": self._proj_archaeology_merge,
            "quarantine": self._proj_quarantine,
            "unquarantine": self._proj_unquarantine,
            "mutate_to_ghost": self._proj_mutate_to_ghost,
            "reparent": self._proj_reparent,
            "score_update": self._proj_score_update,
            "taint_update": self._proj_taint_update,
            "decalcify": self._proj_decalcify,
            "restore": self._proj_restore,
        }
        projector = _PROJECTORS.get(event_type)
        if projector:
            if event_type in {
                "tombstone",
                "archaeology_merge",
                "quarantine",
                "taint_update",
                "reparent",
            }:
                await projector(conn, fact_id, payload, tenant_id=tenant_id)
            else:
                await projector(conn, fact_id, payload)
        else:
            # Unknown event type — log but don't fail.
            # The event is still recorded immutably in entity_events.
            logger.info(
                "No projector for event_type=%s on fact %d — event stored but not projected",
                event_type,
                fact_id,
            )
    # ── Individual Projectors ────────────────────────────────────────
    async def _proj_decalcify(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        """Protocol Ω₃-E: Reduce certainty over time to prevent stagnation."""
        decay_factor = payload.get("decay_factor", 0.95)
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        facts_columns = await self._facts_columns(conn)
        has_consensus_column = "consensus_score" in facts_columns
        # 1. Fetch current scores
        score_query = (
            "SELECT consensus_score, confidence FROM facts WHERE id = ?"
            if has_consensus_column
            else "SELECT json_extract(metadata, '$.consensus_score'), confidence FROM facts WHERE id = ?"
        )
        async with conn.execute(score_query, (fact_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
        current_score_raw, confidence = row
        current_score = float(current_score_raw) if current_score_raw is not None else 1.0
        new_score = round(current_score * decay_factor, 3)
        # 2. State demotion (Verified -> Tentative -> Disputed)
        new_confidence = confidence
        if new_score < 1.4 and confidence == "verified":
            new_confidence = "tentative"
        elif new_score < 0.6 and confidence != "disputed":
            new_confidence = "disputed"
        if has_consensus_column:
            await conn.execute(
                "UPDATE facts SET confidence = ?, updated_at = ?, consensus_score = ? WHERE id = ?",
                (new_confidence, ts, new_score, fact_id),
            )
            return
        query = (
            "UPDATE facts SET confidence = ?, updated_at = ?, "
            "metadata = CASE "
            "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
            "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
            "END "
            "WHERE id = ?"
        )
        await conn.execute(query, (new_confidence, ts, new_score, fact_id))
    async def _proj_deprecate(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        reason = payload.get("reason", "deprecated")
        # Ω₂: Robust Metadata Projection.
        # If meta is encrypted (v6_aesgcm:...), json_set will fail.
        # We skip the json_set for encrypted blobs to prevent OperationalError.
        await conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "metadata = CASE "
            "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
            "  ELSE json_set(COALESCE(metadata, '{}'), '$.deprecation_reason', ?) "
            "END "
            "WHERE id = ?",
            (ts, ts, reason, fact_id),
        )
    async def _proj_mutate_to_ghost(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        """Project an evaporation event into ghost state."""
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "UPDATE facts SET fact_type = 'ghost', updated_at = ? WHERE id = ?",
            (ts, fact_id),
        )
    async def _proj_tombstone(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
        tenant_id: str | None = None,
    ) -> None:
        reason = payload.get("reason", "tombstoned")
        ts = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
        query = (
            "UPDATE facts SET valid_until = ?, is_tombstoned = 1, updated_at = ?, "
            "metadata = CASE "
            "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
            "  ELSE json_set(COALESCE(metadata, '{}'), '$.tombstoned_at', ?, "
            "                '$.tombstone_reason', ?) "
            "END "
            "WHERE id = ?"
        )
        await conn.execute(query, (ts, ts, ts, reason, fact_id))
        # Ω₁₃: Propagate TAINTED status to descendants
        resolved_tenant_id = tenant_id or await self._get_fact_tenant_id(conn, fact_id)
        graph = AsyncCausalGraph(conn)
        report = await graph.propagate_taint(fact_id, tenant_id=resolved_tenant_id)
        logger.info(
            "Ω₁₃ Taint (Tombstone) propagated from fact %d: %d nodes affected",
            fact_id,
            report.affected_count,
        )
    async def _proj_archaeology_merge(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
        tenant_id: str | None = None,
    ) -> None:
        """Archive a superseded fact without treating it as invalidated/tainted."""
        ts = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
        reason = payload.get("reason", "archaeology-merged")
        replacement_fact_id = payload.get("replacement_fact_id")
        metadata_column = await self._metadata_column(conn)
        query = "UPDATE facts SET valid_until = ?, is_tombstoned = 1"
        params: list[Any] = [ts]
        facts_columns = await self._facts_columns(conn)
        if "updated_at" in facts_columns:
            query += ", updated_at = ?"
            params.append(ts)
        if metadata_column:
            query += (
                f", {metadata_column} = CASE "
                f"  WHEN {metadata_column} LIKE 'v6_aesgcm:%' THEN {metadata_column} "
                f"  ELSE json_set(COALESCE({metadata_column}, '{{}}'), "
                "                '$.tombstoned_at', ?, "
                "                '$.tombstone_reason', ?, "
                "                '$.archaeology_replacement_fact_id', ?) "
                "END"
            )
            params.extend([ts, reason, replacement_fact_id])
        query += " WHERE id = ?"
        params.append(fact_id)
        if "tenant_id" in facts_columns:
            query += " AND tenant_id = ?"
            params.append(tenant_id or await self._get_fact_tenant_id(conn, fact_id))
        await conn.execute(query, tuple(params))
    async def _proj_quarantine(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
        tenant_id: str | None = None,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        reason = payload.get("reason", "quarantined")
        await conn.execute(
            "UPDATE facts SET is_quarantined = 1, quarantined_at = ?, "
            "quarantine_reason = ?, updated_at = ? "
            "WHERE id = ?",
            (ts, reason, ts, fact_id),
        )
        # Ω₁₃: Propagate taint status to descendants
        resolved_tenant_id = tenant_id or await self._get_fact_tenant_id(conn, fact_id)
        graph = AsyncCausalGraph(conn)
        report = await graph.propagate_taint(fact_id, tenant_id=resolved_tenant_id)
        logger.info(
            "Ω₁₃ Taint (Quarantine) propagated from fact %d: %d nodes affected",
            fact_id,
            report.affected_count,
        )
    async def _proj_unquarantine(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "UPDATE facts SET is_quarantined = 0, quarantined_at = NULL, "
            "quarantine_reason = NULL, updated_at = ? WHERE id = ?",
            (ts, fact_id),
        )
    async def _proj_score_update(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        score = payload.get("consensus_score")
        confidence = payload.get("confidence")
        facts_columns = await self._facts_columns(conn)
        has_consensus_column = "consensus_score" in facts_columns
        if has_consensus_column and score is not None and confidence is not None:
            await conn.execute(
                "UPDATE facts SET confidence = ?, consensus_score = ? WHERE id = ?",
                (confidence, score, fact_id),
            )
        elif has_consensus_column and score is not None:
            await conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        elif confidence is not None and score is None:
            await conn.execute(
                "UPDATE facts SET confidence = ? WHERE id = ?",
                (confidence, fact_id),
            )
        elif score is not None and confidence is not None:
            await conn.execute(
                "UPDATE facts SET confidence = ?, "
                "metadata = CASE "
                "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
                "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
                "END "
                "WHERE id = ?",
                (confidence, score, fact_id),
            )
        elif score is not None:
            await conn.execute(
                "UPDATE facts SET "
                "metadata = CASE "
                "  WHEN metadata LIKE 'v6_aesgcm:%' THEN metadata "
                "  ELSE json_set(COALESCE(metadata, '{}'), '$.consensus_score', ?) "
                "END "
                "WHERE id = ?",
                (score, fact_id),
            )
        elif confidence is not None:
            await conn.execute(
                "UPDATE facts SET confidence = ? WHERE id = ?",
                (confidence, fact_id),
            )
    async def _proj_taint_update(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
        tenant_id: str | None = None,
    ) -> None:
        """Project taint metadata and confidence through the canonical gateway."""
        resolved_tenant_id = tenant_id or await self._get_fact_tenant_id(conn, fact_id)
        confidence = payload.get("confidence")
        metadata_column = await self._metadata_column(conn)
        facts_columns = await self._facts_columns(conn)
        metadata_value: str | None = None
        if metadata_column:
            async with conn.execute(
                f"SELECT {metadata_column} FROM facts WHERE id = ?",
                (fact_id,),
            ) as cursor:
                row = await cursor.fetchone()
            raw_meta = row[0] if row else None
            if raw_meta:
                encrypter = get_default_encrypter()
                if isinstance(raw_meta, str) and raw_meta.startswith(encrypter.PREFIX):
                    meta = encrypter.decrypt_json(raw_meta, tenant_id=resolved_tenant_id) or {}
                    meta.update(
                        {
                            "taint_status": payload["taint_status"],
                            "tainted_by": payload["tainted_by"],
                            "taint_timestamp": payload["taint_timestamp"],
                        }
                    )
                    metadata_value = encrypter.encrypt_json(meta, tenant_id=resolved_tenant_id)
                else:
                    try:
                        meta = json.loads(raw_meta)
                    except (TypeError, json.JSONDecodeError):
                        metadata_value = None
                    else:
                        meta.update(
                            {
                                "taint_status": payload["taint_status"],
                                "tainted_by": payload["tainted_by"],
                                "taint_timestamp": payload["taint_timestamp"],
                            }
                        )
                        metadata_value = json.dumps(meta)
            elif raw_meta in ("", None):
                metadata_value = json.dumps(
                    {
                        "taint_status": payload["taint_status"],
                        "tainted_by": payload["tainted_by"],
                        "taint_timestamp": payload["taint_timestamp"],
                    }
                )
        set_clauses: list[str] = []
        params: list[Any] = []
        if confidence is not None:
            set_clauses.append("confidence = ?")
            params.append(confidence)
        if metadata_column and metadata_value is not None:
            set_clauses.append(f"{metadata_column} = ?")
            params.append(metadata_value)
        if "updated_at" in facts_columns:
            set_clauses.append("updated_at = ?")
            params.append(payload.get("taint_timestamp") or datetime.now(timezone.utc).isoformat())
        if not set_clauses:
            return
        query = f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(fact_id)
        if "tenant_id" in facts_columns:
            query += " AND tenant_id = ?"
            params.append(resolved_tenant_id)
        await conn.execute(query, tuple(params))
    async def _proj_reparent(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
        tenant_id: str | None = None,
    ) -> None:
        """Reassign a fact's causal parent through the canonical gateway."""
        resolved_tenant_id = tenant_id or await self._get_fact_tenant_id(conn, fact_id)
        new_parent = payload.get("parent_decision_id")
        if new_parent is None:
            return
        facts_columns = await self._facts_columns(conn)
        metadata_column = await self._metadata_column(conn)
        set_clauses: list[str] = []
        params: list[Any] = []
        if "parent_decision_id" in facts_columns:
            set_clauses.append("parent_decision_id = ?")
            params.append(new_parent)
        if "parent_id" in facts_columns:
            set_clauses.append("parent_id = ?")
            params.append(new_parent)
        metadata_value: str | None = None
        if metadata_column and "parent_decision_id" not in facts_columns and "parent_id" not in facts_columns:
            async with conn.execute(
                f"SELECT {metadata_column} FROM facts WHERE id = ?",
                (fact_id,),
            ) as cursor:
                row = await cursor.fetchone()
            raw_meta = row[0] if row else None
            if raw_meta:
                encrypter = get_default_encrypter()
                if isinstance(raw_meta, str) and raw_meta.startswith(encrypter.PREFIX):
                    meta = encrypter.decrypt_json(raw_meta, tenant_id=resolved_tenant_id) or {}
                    meta["parent_decision_id"] = new_parent
                    metadata_value = encrypter.encrypt_json(meta, tenant_id=resolved_tenant_id)
                else:
                    try:
                        meta = json.loads(raw_meta)
                    except (TypeError, json.JSONDecodeError):
                        metadata_value = None
                    else:
                        meta["parent_decision_id"] = new_parent
                        metadata_value = json.dumps(meta)
            else:
                metadata_value = json.dumps({"parent_decision_id": new_parent})
        if metadata_column and metadata_value is not None:
            set_clauses.append(f"{metadata_column} = ?")
            params.append(metadata_value)
        if "updated_at" in facts_columns:
            set_clauses.append("updated_at = ?")
            params.append(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
        if not set_clauses:
            return
        query = f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(fact_id)
        if "tenant_id" in facts_columns:
            query += " AND tenant_id = ?"
            params.append(resolved_tenant_id)
        await conn.execute(query, tuple(params))
    async def _proj_restore(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "UPDATE facts SET valid_until = NULL, is_tombstoned = 0, "
            "tombstoned_at = NULL, is_quarantined = 0, quarantined_at = NULL, "
            "quarantine_reason = NULL, updated_at = ? WHERE id = ?",
            (ts, fact_id),
        )
    # ── Audit / Verification ─────────────────────────────────────────
    async def verify_chain(
        self,
        conn: aiosqlite.Connection,
        entity_id: int,
    ) -> dict[str, Any]:
        """Cryptographic audit of the event chain for a single entity.
        Recalculates every signature and verifies back-pointers.
        Returns a structured audit result.
        """
        async with conn.execute(
            "SELECT id, entity_id, tenant_id, event_type, payload, "
            "prev_hash, signature "
            "FROM entity_events "
            "WHERE entity_id = ? "
            "ORDER BY id ASC",
            (entity_id,),
        ) as cursor:
            findings: list[str] = []
            last_sig = "GENESIS"
            count = 0
            async for row in cursor:
                count += 1
                eid, ent_id, tid, etype, payload_str, prev_hash, sig = row
                # 1. Hash continuity
                if prev_hash != last_sig:
                    findings.append(
                        f"DISCONTINUITY: Event {eid} prev_hash={prev_hash} "
                        f"but last signature was {last_sig}"
                    )
                # 2. Signature integrity
                chain_input = f"{eid}:{ent_id}:{tid}:{etype}:{payload_str}:{prev_hash}"
                expected = hashlib.sha3_256(chain_input.encode()).hexdigest()
                if sig != expected:
                    findings.append(
                        f"TAMPER_DETECTED: Event {eid} sig={sig[:16]}… expected={expected[:16]}…"
                    )
                last_sig = sig
        return {
            "entity_id": entity_id,
            "status": "VALID" if not findings else "CORRUPT",
            "events_audited": count,
            "integrity_score": (1.0 if not findings else max(0.0, (count - len(findings)) / count)),
            "findings": findings or ["Entity event chain: 100% integrity."],
        }
    async def replay_state(
        self,
        conn: aiosqlite.Connection,
        entity_id: int,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        """Reconstruct the projected state of an entity from its event log.
        This is the deterministic fold: state(id, t) = reduce(events, genesis).
        If as_of is provided (ISO 8601), only events up to that timestamp
        are replayed.
        """
        query = "SELECT event_type, payload FROM entity_events WHERE entity_id = ? "
        params: list[Any] = [entity_id]
        if as_of:
            query += "AND timestamp <= ? "
            params.append(as_of)
        query += "ORDER BY id ASC"
        state: dict[str, Any] = {}
        async with conn.execute(query, params) as cursor:
            async for row in cursor:
                event_type, payload_str = row
                try:
                    payload = json.loads(payload_str)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                state["_last_event_type"] = event_type
                state.update(payload)
        return state
# ── Module-level singleton ───────────────────────────────────────────
MUTATION_ENGINE = FactMutationEngine()
