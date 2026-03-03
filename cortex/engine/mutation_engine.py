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
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

__all__ = ["FactMutationEngine"]

logger = logging.getLogger("cortex.mutation_engine")

# Current payload schema version written by MOSKV-1.
_PAYLOAD_SCHEMA_VERSION = "1"


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
        event_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, default=str)

        # ── 1. Hash-chain: link to the last event for this entity ────
        prev_hash = await self._get_last_hash(conn, fact_id)
        chain_input = f"{event_id}:{fact_id}:{tenant_id}:{event_type}:{payload_str}:{prev_hash}"
        signature = hashlib.sha3_256(chain_input.encode()).hexdigest()

        # ── 2. Atomic transaction: INSERT event + UPDATE projection ──
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
        await self._project(conn, fact_id, event_type, payload)

        if commit:
            await conn.commit()

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
        cursor = await conn.execute(
            "SELECT signature FROM entity_events "
            "WHERE entity_id = ? "
            "ORDER BY timestamp DESC, rowid DESC "
            "LIMIT 1",
            (entity_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else "GENESIS"

    # ── Projection Layer (MOSKV-1 specific) ──────────────────────────

    async def _project(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
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
            "quarantine": self._proj_quarantine,
            "unquarantine": self._proj_unquarantine,
            "score_update": self._proj_score_update,
            "decalcify": self._proj_decalcify,
            "restore": self._proj_restore,
        }

        projector = _PROJECTORS.get(event_type)
        if projector:
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

        # 1. Fetch current scores
        cursor = await conn.execute(
            "SELECT consensus_score, confidence FROM facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return

        current_score, confidence = row
        new_score = round((current_score or 1.0) * decay_factor, 3)

        # 2. State demotion (Verified -> Tentative -> Disputed)
        new_confidence = confidence
        if new_score < 1.4 and confidence == "verified":
            new_confidence = "tentative"
        elif new_score < 0.6 and confidence != "disputed":
            new_confidence = "disputed"

        await conn.execute(
            "UPDATE facts SET consensus_score = ?, confidence = ?, updated_at = ? WHERE id = ?",
            (new_score, new_confidence, ts, fact_id),
        )

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
            "meta = CASE "
            "  WHEN meta LIKE 'v6_aesgcm:%' THEN meta "
            "  ELSE json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "END "
            "WHERE id = ?",
            (ts, ts, reason, fact_id),
        )

    async def _proj_tombstone(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "UPDATE facts SET valid_until = ?, is_tombstoned = 1, "
            "tombstoned_at = ?, updated_at = ? WHERE id = ?",
            (ts, ts, ts, fact_id),
        )

    async def _proj_quarantine(
        self,
        conn: aiosqlite.Connection,
        fact_id: int,
        payload: dict,
    ) -> None:
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        reason = payload.get("reason", "quarantined")
        await conn.execute(
            "UPDATE facts SET is_quarantined = 1, quarantined_at = ?, "
            "quarantine_reason = ?, updated_at = ? "
            "WHERE id = ?",
            (ts, reason, ts, fact_id),
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
        if score is not None and confidence:
            await conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
                (score, confidence, fact_id),
            )
        elif score is not None:
            await conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )

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
        cursor = await conn.execute(
            "SELECT id, entity_id, tenant_id, event_type, payload, "
            "prev_hash, signature "
            "FROM entity_events "
            "WHERE entity_id = ? "
            "ORDER BY timestamp ASC, rowid ASC",
            (entity_id,),
        )

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
        query += "ORDER BY timestamp ASC, rowid ASC"

        cursor = await conn.execute(query, params)

        state: dict[str, Any] = {}
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
