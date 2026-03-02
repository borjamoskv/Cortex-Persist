"""
CORTEX v5.0 — Auto-Compaction Engine.

Fights context rot by deduplicating, consolidating, and pruning stale facts.
The compactor completes the memory lifecycle trinity:
  - pruner.py  → embedding lifecycle
  - compression.py → storage optimization
  - compactor.py → content-level compaction (this module)

Strategies:
  - DEDUP: SHA-256 exact + Levenshtein near-duplicate detection
  - MERGE_ERRORS: Consolidate repeated error facts into one
  - STALENESS_PRUNE: Deprecate old, low-consensus facts

Design: Zero data loss — originals are deprecated, never deleted.
Ledger hash-chain remains intact. time_travel still works.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compactor")


_LOG_FMT = "Compactor [%s] %s"

__all__ = [
    "CompactionStrategy",
    "CompactionResult",
    "compact",
    "compact_session",
    "get_compaction_stats",
]


# ─── Strategy Enum ───────────────────────────────────────────────────


class CompactionStrategy(str, Enum):
    """Available compaction strategies."""

    DEDUP = "dedup"
    MERGE_ERRORS = "merge_errors"
    STALENESS_PRUNE = "staleness_prune"
    TTL_PRUNE = "ttl_prune"
    DRIFT_CHECK = "drift_check"

    @classmethod
    def all(cls) -> list[CompactionStrategy]:
        return list(cls)


# ─── Result Dataclass ────────────────────────────────────────────────


@dataclass
class CompactionResult:
    """Outcome of a compaction run."""

    project: str
    strategies_applied: list[str] = field(default_factory=list)
    original_count: int = 0
    compacted_count: int = 0
    deprecated_ids: list[int] = field(default_factory=list)
    new_fact_ids: list[int] = field(default_factory=list)
    dry_run: bool = False
    details: list[str] = field(default_factory=list)

    @property
    def reduction(self) -> int:
        return self.original_count - self.compacted_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "strategies_applied": self.strategies_applied,
            "original_count": self.original_count,
            "compacted_count": self.compacted_count,
            "reduction": self.reduction,
            "deprecated_ids": self.deprecated_ids,
            "new_fact_ids": self.new_fact_ids,
            "dry_run": self.dry_run,
            "details": self.details,
        }


# ─── Main Entry Point ───────────────────────────────────────────────


def _apply_dedup_strategy(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
    dry_run: bool,
    similarity_threshold: float,
) -> None:
    from cortex.compaction.strategies.dedup import execute_dedup

    prev_count = len(result.deprecated_ids)
    execute_dedup(engine, project, result, dry_run, similarity_threshold)
    if len(result.deprecated_ids) > prev_count:
        result.strategies_applied.append(str(CompactionStrategy.DEDUP.value))


async def _apply_strategies(
    engine: CortexEngine,
    project: str,
    strategies: list[CompactionStrategy],
    result: CompactionResult,
    dry_run: bool,
    similarity_threshold: float,
    max_age_days: int,
    min_consensus: float,
) -> None:
    """Execute selected compaction strategies."""
    if CompactionStrategy.DEDUP in strategies:
        from cortex.compaction.strategies.dedup import execute_dedup

        prev_count = len(result.deprecated_ids)
        await execute_dedup(engine, project, result, dry_run, similarity_threshold)
        if len(result.deprecated_ids) > prev_count:
            result.strategies_applied.append(str(CompactionStrategy.DEDUP.value))

    if CompactionStrategy.MERGE_ERRORS in strategies:
        from cortex.compaction.strategies.merge_errors import execute_merge_errors

        prev_count = len(result.deprecated_ids)
        await execute_merge_errors(engine, project, result, dry_run)
        if len(result.deprecated_ids) > prev_count:
            result.strategies_applied.append(str(CompactionStrategy.MERGE_ERRORS.value))

    if CompactionStrategy.STALENESS_PRUNE in strategies:
        from cortex.compaction.strategies.staleness import execute_staleness_prune

        prev_count = len(result.deprecated_ids)
        await execute_staleness_prune(engine, project, result, dry_run, max_age_days, min_consensus)
        if len(result.deprecated_ids) > prev_count:
            result.strategies_applied.append(str(CompactionStrategy.STALENESS_PRUNE.value))

    if CompactionStrategy.TTL_PRUNE in strategies:
        prev_count = len(result.deprecated_ids)
        await _apply_ttl_prune(engine, project, result, dry_run)
        if len(result.deprecated_ids) > prev_count:
            result.strategies_applied.append(str(CompactionStrategy.TTL_PRUNE.value))

    if CompactionStrategy.DRIFT_CHECK in strategies:
        await _apply_drift_check(engine, project, result)


async def compact(
    engine: CortexEngine,
    project: str,
    strategies: list[CompactionStrategy] | None = None,
    dry_run: bool = False,
    similarity_threshold: float = 0.85,
    max_age_days: int = 90,
    min_consensus: float = 0.5,
) -> CompactionResult:
    """Run compaction on a project. Main entry point.

    Applies selected strategies in order, deprecating originals
    and creating consolidated facts. Zero data loss.
    """
    if strategies is None:
        strategies = CompactionStrategy.all()

    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    )
    count_before = (await cursor.fetchone())[0]

    result = CompactionResult(project=project, original_count=count_before, dry_run=dry_run)

    await _apply_strategies(
        engine,
        project,
        strategies,
        result,
        dry_run,
        similarity_threshold,
        max_age_days,
        min_consensus,
    )

    # Final count
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    )
    count_after = (await cursor.fetchone())[0]
    result.compacted_count = count_after

    # Log compaction
    if not dry_run and (result.deprecated_ids or result.new_fact_ids):
        await _log_compaction(
            conn,
            project=project,
            strategies=list(result.strategies_applied),
            original_ids=result.deprecated_ids,
            new_fact_ids=result.new_fact_ids,
            facts_before=count_before,
            facts_after=count_after,
        )

    logger.info(
        "Compaction [%s] complete: %d → %d facts (-%d)%s",
        project,
        count_before,
        count_after,
        result.reduction,
        " (dry-run)" if dry_run else "",
    )
    return result


# ─── Session Compaction ──────────────────────────────────────────────


_TYPE_ORDER = [
    "axiom",
    "decision",
    "rule",
    "error",
    "knowledge",
    "ghost",
    "intent",
    "schema",
]


async def compact_session(
    engine: CortexEngine,
    project: str,
    max_facts: int = 50,
) -> str:
    """Prepare compressed context string for LLM re-injection.

    Instead of sending 500 facts to the LLM, we send a categorized,
    compacted view.
    """
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT fact_type, content, consensus_score, created_at "
        "FROM facts "
        "WHERE project = ? AND valid_until IS NULL "
        "ORDER BY (consensus_score * 0.7 + "
        "(1.0 / (1.0 + (julianday('now') - julianday(created_at)))) * 0.3) DESC "
        "LIMIT ?",
        (project, max_facts),
    )
    rows = await cursor.fetchall()

    if not rows:
        return f"No active facts for project '{project}'."

    grouped: dict[str, list[Any]] = {t: [] for t in _TYPE_ORDER}
    grouped["other"] = []

    for row in rows:
        ftype = row[0]
        if ftype in grouped:
            grouped[ftype].append(row)
        else:
            grouped["other"].append(row)

    lines = [f"# {project} — Active Memory State", ""]
    for ftype in _TYPE_ORDER:
        if grouped[ftype]:
            _append_type_section(lines, ftype, grouped[ftype])

    if grouped["other"]:
        _append_type_section(lines, "other", grouped["other"])

    return "\n".join(lines)


def _append_type_section(lines: list[str], fact_type: str, facts: list[Any]) -> None:
    """Append a fact type section to the output lines."""
    lines.append(f"## {fact_type.capitalize()} ({len(facts)})")
    lines.append("")
    for row in facts:
        lines.append(f"- {row[1][:200]}")
    lines.append("")


# ─── Stats ───────────────────────────────────────────────────────────


async def get_compaction_stats(
    engine: CortexEngine,
    project: str | None = None,
) -> dict[str, Any]:
    """Get compaction history and statistics."""
    conn = await engine.get_conn()

    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compaction_log'"
    )
    table_exists = await cursor.fetchone()

    if not table_exists:
        return {"total_compactions": 0, "total_deprecated": 0, "history": []}

    query = "SELECT * FROM compaction_log"
    params: list = []
    if project:
        query += " WHERE project = ?"
        params.append(project)
    query += " ORDER BY timestamp DESC LIMIT 20"

    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    history = []
    total_deprecated = 0

    for row in rows:
        original_ids = json.loads(row[4]) if row[4] else []
        total_deprecated += len(original_ids)
        history.append(
            {
                "id": row[0],
                "project": row[2],
                "strategy": row[3],
                "deprecated_count": len(original_ids),
                "new_fact_id": row[5],
                "facts_before": row[6],
                "facts_after": row[7],
                "timestamp": row[8],
            }
        )

    return {
        "total_compactions": len(rows),
        "total_deprecated": total_deprecated,
        "history": history,
    }


# ─── TTL Prune (AX-019: Persist With Decay) ─────────────────────────


async def _apply_ttl_prune(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
    dry_run: bool,
) -> None:
    """Deprecate facts that have exceeded their type-specific TTL.

    Uses the canonical TTL policy from cortex.axioms.ttl.
    Immortal types (axiom, decision, bridge, rule, report, evolution) are skipped.
    Routes all mutations through FactMutationEngine (Solid-State Substrate).
    """
    from cortex.axioms.ttl import FACT_TTL, is_expired

    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT id, fact_type, created_at, tenant_id "
        "FROM facts "
        "WHERE project = ? AND valid_until IS NULL",
        (project,),
    )
    rows = await cursor.fetchall()

    from datetime import datetime, timezone

    from cortex.axioms.ttl import is_tombstonable

    now = datetime.now(tz=timezone.utc)
    expired_ids: list[tuple[int, str]] = []  # (fact_id, tenant_id)
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

    if not expired_ids:
        return

    if dry_run:
        result.details.append(f"TTL_PRUNE: would deprecate {len(expired_ids)} expired facts")
        if tombstonable_ids:
            result.details.append(f"TTL_PRUNE: would tombstone {len(tombstonable_ids)} of those")
        result.deprecated_ids.extend(fid for fid, _ in expired_ids)
        return

    from cortex.engine.mutation_engine import MUTATION_ENGINE

    ts = now.isoformat()
    tombstone_set = {fid for fid, _ in tombstonable_ids}

    for fid, tid in expired_ids:
        if fid in tombstone_set:
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=fid,
                tenant_id=tid,
                event_type="tombstone",
                payload={"timestamp": ts, "reason": "ttl_expired"},
                signer="compactor:ttl_prune",
                commit=False,
            )
        else:
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=fid,
                tenant_id=tid,
                event_type="deprecate",
                payload={"timestamp": ts, "reason": "ttl_expired"},
                signer="compactor:ttl_prune",
                commit=False,
            )

    await conn.commit()
    result.deprecated_ids.extend(fid for fid, _ in expired_ids)

    t_count = len(tombstonable_ids)
    e_count = len(expired_ids)

    result.details.append(f"TTL_PRUNE: deprecated {e_count} expired facts ({t_count} tombstoned)")
    logger.info(
        _LOG_FMT,
        project,
        f"TTL prune: {e_count} facts expired, {t_count} tombstoned",
    )


# ─── Drift Check ─────────────────────────────────────────────────────


async def _apply_drift_check(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
) -> None:
    """Check L2 vector space topological health.

    Non-destructive — appends diagnostic info to result.details only.
    Does not deprecate or modify any facts.
    """
    try:
        import numpy as np

        from cortex.memory.drift import DriftMonitor, model_hash_from_name

        # Get the embedder info from engine
        embedder = getattr(engine, "_embedder", None)
        model_name = getattr(embedder, "model_name", "all-MiniLM-L6-v2")
        model_hash = model_hash_from_name(model_name)

        # Read embeddings from the facts_embeddings table
        conn = await engine.get_conn()
        cursor = await conn.execute(
            "SELECT embedding FROM fact_embeddings "
            "WHERE fact_id IN ("
            "  SELECT id FROM facts WHERE project = ? AND valid_until IS NULL"
            ")",
            (project,),
        )
        rows = await cursor.fetchall()

        if not rows or len(rows) < 10:
            result.details.append(f"DRIFT_CHECK: insufficient vectors ({len(rows) if rows else 0})")
            result.strategies_applied.append(str(CompactionStrategy.DRIFT_CHECK.value))
            return

        # Convert embeddings to numpy
        embeddings = np.array([np.frombuffer(row[0], dtype=np.float32) for row in rows])

        from pathlib import Path

        sig_dir = Path.home() / ".cortex" / "drift"
        monitor = DriftMonitor(model_hash=model_hash, signature_dir=sig_dir)

        baseline = monitor.load_baseline()
        if baseline is None:
            sig = monitor.checkpoint(embeddings)
            result.details.append(
                f"DRIFT_CHECK: baseline created (n={sig.n_vectors}, "
                f"spectral_gap={sig.spectral_gap:.3f})"
            )
        else:
            health_result = monitor.health(embeddings, baseline)
            health = health_result["topological_health"]
            result.details.append(f"DRIFT_CHECK: health={health:.3f} ({health_result['detail']})")

        result.strategies_applied.append(str(CompactionStrategy.DRIFT_CHECK.value))

    except (ImportError, ValueError, OSError, RuntimeError) as e:
        result.details.append(f"DRIFT_CHECK: skipped ({e})")
        logger.warning(_LOG_FMT, project, f"Drift check failed: {e}")


# ─── Internal ────────────────────────────────────────────────────────


async def _log_compaction(
    conn: aiosqlite.Connection,
    project: str,
    strategies: list[str],
    original_ids: list[int],
    new_fact_ids: list[int],
    facts_before: int,
    facts_after: int,
) -> None:
    """Log a compaction event to the compaction_log table."""
    try:
        await conn.execute(
            "INSERT INTO compaction_log "
            "(project, strategy, original_ids, new_fact_id, facts_before, facts_after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                project,
                ",".join(strategies),
                json.dumps(original_ids),
                new_fact_ids[0] if new_fact_ids else None,
                facts_before,
                facts_after,
            ),
        )
        await conn.commit()
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.warning("Failed to log compaction: %s", e)
