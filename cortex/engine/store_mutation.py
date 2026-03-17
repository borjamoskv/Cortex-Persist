"""Logic for fact invalidation, deprecation and purge (demolition)."""
from __future__ import annotations

import logging
from typing import Any, Optional
import aiosqlite
from cortex.utils.canonical import now_iso
from cortex.immune.quarantine import BlastRadiusReport, evaluate_demolition

logger = logging.getLogger("cortex.engine.mutation")

async def deprecate_impl_logic(
    mixin_instance: Any, conn: aiosqlite.Connection, fact_id: int, reason: Optional[str], tenant_id: str
) -> bool:
    from cortex.engine.mutation_engine import MUTATION_ENGINE
    from cortex.engine.causality import AsyncCausalGraph
    
    ts = now_iso()
    async with conn.execute(
        "SELECT project FROM facts WHERE id = ? AND tenant_id = ? AND is_tombstoned = 0",
        (fact_id, tenant_id)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False
    project = row[0]
    
    await MUTATION_ENGINE.apply(
        conn, fact_id=fact_id, tenant_id=tenant_id, event_type="deprecate",
        payload={"reason": reason or "deprecated", "timestamp": ts},
        signer="store_mixin:deprecate", commit=False
    )
    await AsyncCausalGraph(conn).propagate_taint(fact_id=fact_id, tenant_id=tenant_id)
    try:
        await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
    except Exception:
        pass
    await mixin_instance._log_transaction(conn, project, "deprecate", {"fact_id": fact_id, "reason": reason})
    return True

async def invalidate_impl_logic(
    mixin_instance: Any, conn: aiosqlite.Connection, fact_id: int, reason: Optional[str], tenant_id: str
) -> bool:
    from cortex.engine.mutation_engine import MUTATION_ENGINE
    from cortex.engine.causality import AsyncCausalGraph
    
    ts = now_iso()
    async with conn.execute(
        "SELECT project FROM facts WHERE id = ? AND tenant_id = ? AND is_tombstoned = 0",
        (fact_id, tenant_id)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False
    project = row[0]

    await MUTATION_ENGINE.apply(
        conn, fact_id=fact_id, tenant_id=tenant_id, event_type="tombstone",
        payload={"reason": reason or "invalidated", "timestamp": ts},
        signer="store_mixin:invalidate", commit=False
    )
    await MUTATION_ENGINE.apply(
        conn, fact_id=fact_id, tenant_id=tenant_id, event_type="score_update",
        payload={"confidence": "C1", "consensus_score": 0.0},
        signer="store_mixin:invalidate:force", commit=False
    )
    await AsyncCausalGraph(conn).propagate_taint(fact_id=fact_id, tenant_id=tenant_id)
    try:
        await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
    except Exception:
        pass
    await mixin_instance._log_transaction(conn, project, "invalidate", {"fact_id": fact_id, "reason": reason})
    return True

async def purge_logic(
    mixin_instance: Any, fact_id: int, tenant_id: str, force: bool
) -> bool:
    async with mixin_instance.session() as conn:
        from cortex.engine.causality import AsyncCausalGraph
        graph = AsyncCausalGraph(conn)
        async with conn.execute(
            "SELECT project, fact_type FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        project, fact_type = row
        dep_count = await graph.calculate_blast_radius(fact_id, tenant_id)
        criticality = 0.5 if fact_type == "rule" else 0.0
        criticality += min(0.4, dep_count * 0.1)
        report = BlastRadiusReport(0, 0, 0, dep_count, criticality)
        decision = evaluate_demolition(report, True, fact_type == "rule")
        if not decision.allowed and not force:
            if decision.requires_quarantine:
                await mixin_instance.invalidate(
                    fact_id, reason=f"Quarantined: {decision.reason}", conn=conn, tenant_id=tenant_id
                )
            raise RuntimeError(f"Demolition Denied: {decision.reason}")
        await conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        await conn.execute(
            "DELETE FROM causal_edges WHERE fact_id = ? OR parent_id = ?",
            (fact_id, fact_id)
        )
        await mixin_instance._log_transaction(
            conn, project, "purge", {"fact_id": fact_id, "blast_radius": dep_count}
        )
        await conn.commit()
        return True
