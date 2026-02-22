"""
CORTEX v4.0 — Reflection Engine.

Automated post-mortem loop + semantic injection for system prompts.
Transforms static memory into learned intuition by:
1. Storing structured reflections (errors, decisions, learnings) after each session.
2. Injecting the top-K semantically relevant reflections before each new session.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.reflection")

# Fact types considered "learnable" for injection
LEARNABLE_TYPES = ("reflection", "error", "meta_learning")

# Default tags for auto-generated reflections
AUTO_TAGS = ["post-mortem", "auto-generated"]


@dataclass(frozen=True, slots=True)
class Reflection:
    """A structured post-mortem reflection."""

    project: str
    summary: str
    errors: list[str]
    decisions: list[str]
    timestamp: str

    def to_content(self) -> str:
        """Serialize to a storable fact content string."""
        parts = [f"[REFLECTION] {self.summary}"]
        for err in self.errors:
            parts.append(f"  ✗ Error: {err}")
        for dec in self.decisions:
            parts.append(f"  → Decision: {dec}")
        parts.append(f"  @ {self.timestamp}")
        return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class InjectedLearning:
    """A retrieved learning ready for system_prompt injection."""

    fact_id: int
    project: str
    content: str
    fact_type: str
    score: float
    created_at: str


def generate_reflection(
    engine: CortexEngine,
    project: str,
    summary: str,
    errors: list[str] | None = None,
    decisions: list[str] | None = None,
    source: str = "auto-reflect",
) -> int:
    """Store a structured post-mortem reflection.

    Args:
        engine: Active CortexEngine instance.
        project: Project namespace.
        summary: What happened this session / what was learned.
        errors: Errors encountered and how they were solved.
        decisions: Key architectural or design decisions made.
        source: Origin tag (default "auto-reflect").

    Returns:
        The fact_id of the stored reflection.
    """
    reflection = Reflection(
        project=project,
        summary=summary,
        errors=errors or [],
        decisions=decisions or [],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    content = reflection.to_content()
    fact_id = engine.store_sync(
        project=project,
        content=content,
        fact_type="reflection",
        tags=AUTO_TAGS,
        confidence="confirmed",
        source=source,
    )
    logger.info("Stored reflection #%d for project '%s'", fact_id, project)
    return fact_id


def inject_reflections(
    engine: CortexEngine,
    context_hint: str,
    project: str | None = None,
    top_k: int = 5,
) -> list[InjectedLearning]:
    """Retrieve the top-K most relevant past learnings for system_prompt injection.

    Uses hybrid search (semantic + text via RRF) against facts of type
    'reflection', 'error', and 'meta_learning' — the "learnable" subset.

    Args:
        engine: Active CortexEngine instance.
        context_hint: Description of what the next session will focus on.
        project: Optional project filter.
        top_k: Number of learnings to retrieve (default 5).

    Returns:
        List of InjectedLearning, ordered by relevance score (desc).
    """
    conn = engine._get_sync_conn()
    results = _hybrid_search_learnable(conn, context_hint, project, top_k)

    learnings = []
    for row in results:
        learnings.append(
            InjectedLearning(
                fact_id=row["fact_id"],
                project=row["project"],
                content=row["content"],
                fact_type=row["fact_type"],
                score=row["score"],
                created_at=row["created_at"],
            )
        )
    return learnings


def format_injection_markdown(learnings: list[InjectedLearning]) -> str:
    """Format retrieved learnings as a markdown block for system_prompt injection.

    Args:
        learnings: List of InjectedLearning from inject_reflections().

    Returns:
        Markdown string ready to be prepended to system_prompt.
    """
    if not learnings:
        return "<!-- No prior reflections found for this context. -->"

    lines = [
        "## 🧠 CORTEX Reflections (Auto-Injected)",
        "",
        "The following are your most relevant past learnings for this session:",
        "",
    ]
    for i, lr in enumerate(learnings, 1):
        lines.append(f"### {i}. [{lr.project}] ({lr.fact_type}) — score {lr.score:.3f}")
        lines.append(f"> {lr.content}")
        lines.append(f"_Stored: {lr.created_at}_")
        lines.append("")

    lines.append("---")
    return "\n".join(lines)


def format_injection_json(learnings: list[InjectedLearning]) -> str:
    """Format retrieved learnings as JSON for programmatic consumption."""
    data = [
        {
            "fact_id": lr.fact_id,
            "project": lr.project,
            "content": lr.content,
            "fact_type": lr.fact_type,
            "score": lr.score,
            "created_at": lr.created_at,
        }
        for lr in learnings
    ]
    return json.dumps(data, indent=2, ensure_ascii=False)


# ─── Internal Helpers ────────────────────────────────────────────────


def _hybrid_search_learnable(
    conn: sqlite3.Connection,
    query: str,
    project: str | None,
    top_k: int,
) -> list[dict]:
    """Hybrid search filtered to learnable fact types only.

    Combines semantic vector search (via sqlite-vec) with full-text search
    using Reciprocal Rank Fusion (RRF), filtered to LEARNABLE_TYPES.
    """
    sem_results = _semantic_arm(conn, query, project, top_k)
    txt_results = _text_arm(conn, query, project, top_k)
    return _fuse_rrf(sem_results, txt_results, top_k)


def _semantic_arm(
    conn: sqlite3.Connection,
    query: str,
    project: str | None,
    top_k: int,
) -> list[dict]:
    """Semantic vector search arm."""
    try:
        from cortex.embeddings import LocalEmbedder

        embedding = LocalEmbedder().embed(query)
    except Exception:
        logger.warning("Embeddings unavailable, falling back to text-only search")
        return []

    type_placeholders = ",".join("?" for _ in LEARNABLE_TYPES)
    project_filter = "AND f.project = ?" if project else ""

    sql = f"""
        SELECT ve.fact_id, ve.distance, f.project, f.content, f.fact_type,
               f.created_at
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        WHERE ve.embedding MATCH ?
          AND k = ?
          AND f.fact_type IN ({type_placeholders})
          {project_filter}
          AND f.deprecated_at IS NULL
        ORDER BY ve.distance
    """
    params: list = [json.dumps(embedding), top_k * 2, *LEARNABLE_TYPES]
    if project:
        params.append(project)

    try:
        cursor = conn.execute(sql, params)
        return [
            {
                "fact_id": row[0],
                "distance": row[1],
                "project": row[2],
                "content": row[3],
                "fact_type": row[4],
                "created_at": row[5],
            }
            for row in cursor.fetchall()
        ]
    except Exception as exc:
        logger.debug("Semantic search failed: %s", exc)
        return []


def _text_arm(
    conn: sqlite3.Connection,
    query: str,
    project: str | None,
    top_k: int,
) -> list[dict]:
    """Full-text search arm via FTS5."""
    type_placeholders = ",".join("?" for _ in LEARNABLE_TYPES)
    project_filter = "AND f.project = ?" if project else ""

    sql = f"""
        SELECT f.id, f.project, f.content, f.fact_type, f.created_at
        FROM facts AS f
        JOIN facts_fts AS fts ON fts.rowid = f.id
        WHERE facts_fts MATCH ?
          AND f.fact_type IN ({type_placeholders})
          {project_filter}
          AND f.deprecated_at IS NULL
        LIMIT ?
    """
    params: list = [query, *LEARNABLE_TYPES]
    if project:
        params.append(project)
    params.append(top_k * 2)

    try:
        cursor = conn.execute(sql, params)
        return [
            {
                "fact_id": row[0],
                "project": row[1],
                "content": row[2],
                "fact_type": row[3],
                "created_at": row[4],
            }
            for row in cursor.fetchall()
        ]
    except Exception as exc:
        logger.debug("Text search failed: %s", exc)
        return []


def _fuse_rrf(
    sem_results: list[dict],
    txt_results: list[dict],
    top_k: int,
) -> list[dict]:
    """Reciprocal Rank Fusion of semantic + text results."""
    rrf_k = 60
    rrf_scores: dict[int, float] = {}
    result_map: dict[int, dict] = {}

    for rank, res in enumerate(sem_results):
        fid = res["fact_id"]
        rrf_scores[fid] = rrf_scores.get(fid, 0.0) + 0.6 / (rrf_k + rank + 1)
        result_map[fid] = res

    for rank, res in enumerate(txt_results):
        fid = res["fact_id"]
        rrf_scores[fid] = rrf_scores.get(fid, 0.0) + 0.4 / (rrf_k + rank + 1)
        if fid not in result_map:
            result_map[fid] = res

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
    merged = []
    for fid in sorted_ids:
        entry = result_map[fid]
        entry["score"] = rrf_scores[fid]
        merged.append(entry)

    return merged
