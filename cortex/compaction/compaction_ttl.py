"""compaction_ttl — TTL Prune strategy for the Auto-Compaction Engine.

Extracted from compactor.py to satisfy the Landauer LOC barrier (≤500).
Implements AX-019 (Persist With Decay): deprecate facts exceeding their
type-specific TTL. Immortal types (axiom, decision, bridge, etc.) are skipped.
All mutations routed through MUTATION_ENGINE (Solid-State Substrate).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.compaction.compactor import CompactionResult
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compactor.ttl")
_LOG_FMT = "Compactor TTL [%s] %s"


def find_expired_facts(
    rows: list[Any],
    now: datetime,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Identify expired and tombstonable facts.

    Returns:
        (expired_ids, tombstonable_ids) — tuples of (fact_id, tenant_id).
    """
    from cortex.axioms.ttl import FACT_TTL, is_expired, is_tombstonable

    expired_ids: list[tuple[int, str]] = []
    tombstonable_ids: list[tuple[int, str]] = []

    for row in rows:
        fact_id, fact_type, created_at_str, tenant_id = row[0], row[1], row[2], row[3]
        if FACT_TTL.get(fact_type) is None:
            continue  # Immortal type

        try:
            created = datetime.fromisoformat(created_at_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_seconds = (now - created).total_seconds()

            if is_expired(fact_type, age_seconds):
                expired_ids.append((fact_id, tenant_id))
                if is_tombstonable(fact_type, age_seconds):
                    tombstonable_ids.append((fact_id, tenant_id))
        except (ValueError, TypeError):
            continue

    return expired_ids, tombstonable_ids


async def commit_ttl_mutations(
    conn: Any,
    expired_ids: list[tuple[int, str]],
    tombstonable_ids: list[tuple[int, str]],
    now: datetime,
) -> None:
    """Commit deprecation or tombstone mutations for expired facts."""
    from cortex.engine.mutation_engine import MUTATION_ENGINE

    ts = now.isoformat()
    tombstone_set = {fid for fid, _ in tombstonable_ids}

    for fid, tid in expired_ids:
        event_type = "tombstone" if fid in tombstone_set else "deprecate"
        await MUTATION_ENGINE.apply(
            conn,
            fact_id=fid,
            tenant_id=tid,
            event_type=event_type,
            payload={"timestamp": ts, "reason": "ttl_expired"},
            signer="compactor:ttl_prune",
            commit=False,
        )

    await conn.commit()


async def apply_ttl_prune(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
    dry_run: bool,
) -> None:
    """Deprecate facts that have exceeded their type-specific TTL.

    Uses the canonical TTL policy from cortex.axioms.ttl.
    Immortal types (axiom, decision, bridge, rule, report, evolution) are skipped.
    """
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT id, fact_type, created_at, tenant_id "
        "FROM facts "
        "WHERE project = ? AND valid_until IS NULL",
        (project,),
    )
    rows = await cursor.fetchall()

    now = datetime.now(tz=timezone.utc)
    expired_ids, tombstonable_ids = find_expired_facts(rows, now)  # type: ignore[reportArgumentType]

    if not expired_ids:
        return

    result.deprecated_ids.extend(fid for fid, _ in expired_ids)

    if dry_run:
        result.details.append(f"TTL_PRUNE: would deprecate {len(expired_ids)} expired facts")
        if tombstonable_ids:
            result.details.append(f"TTL_PRUNE: would tombstone {len(tombstonable_ids)} of those")
        return

    await commit_ttl_mutations(conn, expired_ids, tombstonable_ids, now)

    t_count = len(tombstonable_ids)
    e_count = len(expired_ids)
    result.details.append(f"TTL_PRUNE: deprecated {e_count} expired facts ({t_count} tombstoned)")
    logger.info(_LOG_FMT, project, f"TTL prune: {e_count} facts expired, {t_count} tombstoned")
