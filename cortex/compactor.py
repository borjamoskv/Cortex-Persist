"""
CORTEX v4.1 — Auto-Compaction Engine.

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

import hashlib
import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compactor")


_LOG_FMT = "Compactor [%s] %s"


# ─── Strategy Enum ───────────────────────────────────────────────────


class CompactionStrategy(str, Enum):
    """Available compaction strategies."""

    DEDUP = "dedup"
    MERGE_ERRORS = "merge_errors"
    STALENESS_PRUNE = "staleness_prune"

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

    def to_dict(self) -> dict:
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


def compact(
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

    conn = engine._get_sync_conn()
    count_before = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    ).fetchone()[0]

    result = CompactionResult(
        project=project, original_count=count_before, dry_run=dry_run
    )

    # Dispatch strategies
    if CompactionStrategy.DEDUP in strategies:
        from cortex.compaction.strategies.dedup import execute_dedup
        execute_dedup(engine, project, result, dry_run, similarity_threshold)

    if CompactionStrategy.MERGE_ERRORS in strategies:
        from cortex.compaction.strategies.merge_errors import execute_merge_errors
        execute_merge_errors(engine, project, result, dry_run)

    if CompactionStrategy.STALENESS_PRUNE in strategies:
        from cortex.compaction.strategies.staleness import execute_staleness_prune
        execute_staleness_prune(
            engine, project, result, dry_run, max_age_days, min_consensus
        )

    # Final count
    count_after = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    ).fetchone()[0]
    result.compacted_count = count_after

    # Log compaction
    if not dry_run and result.deprecated_ids:
        _log_compaction(
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


_TYPE_ORDER = ["axiom", "decision", "rule", "error", "knowledge", "ghost", "intent", "schema"]


def compact_session(
    engine: CortexEngine,
    project: str,
    max_facts: int = 50,
) -> str:
    """Prepare compressed context string for LLM re-injection.

    Selects most relevant active facts, groups by type,
    produces dense markdown summary.
    """
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT id, content, fact_type, tags, consensus_score, created_at "
        "FROM facts WHERE project = ? AND valid_until IS NULL "
        "ORDER BY "
        "  CASE fact_type "
        "    WHEN 'axiom' THEN 0 WHEN 'decision' THEN 1 "
        "    WHEN 'rule' THEN 2 WHEN 'error' THEN 3 "
        "    WHEN 'knowledge' THEN 4 WHEN 'ghost' THEN 5 "
        "    ELSE 6 END, "
        "  consensus_score DESC, created_at DESC "
        "LIMIT ?",
        (project, max_facts),
    ).fetchall()

    if not rows:
        return f"# {project}\n\nNo active facts.\n"

    by_type: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        by_type[row[2]].append(row)

    return _format_session_context(project, by_type)


def _format_session_context(project: str, by_type: dict[str, list[tuple]]) -> str:
    """Format grouped facts into markdown context."""
    lines = [f"# {project}", ""]

    for ft in _TYPE_ORDER:
        if ft in by_type:
            _append_type_section(lines, ft, by_type[ft])

    # Remaining types not in the predefined order
    for ft, facts in by_type.items():
        if ft not in _TYPE_ORDER:
            _append_type_section(lines, ft, facts)

    return "\n".join(lines)


def _append_type_section(lines: list[str], fact_type: str, facts: list[tuple]) -> None:
    """Append a fact type section to the output lines."""
    lines.append(f"## {fact_type.capitalize()} ({len(facts)})")
    lines.append("")
    for row in facts:
        lines.append(f"- {row[1][:200]}")
    lines.append("")


# ─── Stats ───────────────────────────────────────────────────────────


def get_compaction_stats(
    engine: CortexEngine,
    project: str | None = None,
) -> dict:
    """Get compaction history and statistics."""
    conn = engine._get_sync_conn()

    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compaction_log'"
    ).fetchone()

    if not table_exists:
        return {"total_compactions": 0, "total_deprecated": 0, "history": []}

    query = "SELECT * FROM compaction_log"
    params: list = []
    if project:
        query += " WHERE project = ?"
        params.append(project)
    query += " ORDER BY timestamp DESC LIMIT 20"

    rows = conn.execute(query, params).fetchall()
    history = []
    total_deprecated = 0

    for row in rows:
        original_ids = json.loads(row[3]) if row[3] else []
        total_deprecated += len(original_ids)
        history.append({
            "id": row[0],
            "project": row[1],
            "strategy": row[2],
            "deprecated_count": len(original_ids),
            "new_fact_id": row[4],
            "facts_before": row[5],
            "facts_after": row[6],
            "timestamp": row[7],
        })

    return {
        "total_compactions": len(rows),
        "total_deprecated": total_deprecated,
        "history": history,
    }


# ─── Internal ────────────────────────────────────────────────────────


def _log_compaction(
    conn,
    project: str,
    strategies: list[str],
    original_ids: list[int],
    new_fact_ids: list[int],
    facts_before: int,
    facts_after: int,
) -> None:
    """Log a compaction event to the compaction_log table."""
    try:
        conn.execute(
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
        conn.commit()
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.warning("Failed to log compaction: %s", e)
