"""MEJORAlo Ledger — session recording and history retrieval."""

import json
import logging
from typing import Any

from cortex.engine import CortexEngine

__all__ = ['record_session', 'get_history']

logger = logging.getLogger("cortex.mejoralo")

_VERSION = "8.0"


def record_session(
    engine: CortexEngine,
    project: str,
    score_before: int,
    score_after: int,
    actions: list[str] | None = None,
) -> int:
    """Record a MEJORAlo audit session in the CORTEX ledger.

    Returns:
        The fact ID of the persisted session record.
    """
    delta = score_after - score_before
    actions_str = "\n".join(f"  - {a}" for a in (actions or []))
    content = (
        f"MEJORAlo v{_VERSION}: Sesión completada.\n"
        f"Score: {score_before} → {score_after} (Δ{delta:+d})\n"
        f"Acciones:\n{actions_str}"
        if actions_str
        else (
            f"MEJORAlo v{_VERSION}: Sesión completada. "
            f"Score: {score_before} → {score_after} (Δ{delta:+d})"
        )
    )

    fact_id = engine.store_sync(
        project=project,
        content=content,
        fact_type="decision",
        tags=["mejoralo", "audit", f"v{_VERSION}"],
        confidence="verified",
        source="cortex-mejoralo",
        meta={
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta,
            "actions": actions or [],
            "version": _VERSION,
        },
    )
    logger.info(
        "Recorded MEJORAlo session #%d for project %s (Δ%+d)",
        fact_id, project, delta,
    )
    return fact_id


def get_history(engine: CortexEngine, project: str, limit: int = 20) -> list[dict[str, Any]]:
    """Retrieve past MEJORAlo sessions from the ledger."""
    conn = engine._get_sync_conn()
    try:
        rows = conn.execute(
            "SELECT id, content, created_at, meta "
            "FROM facts "
            "WHERE project = ? AND fact_type = 'decision' "
            "AND tags LIKE '%mejoralo%' AND valid_until IS NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (project, limit),
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_session(row) for row in rows]


def _row_to_session(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a database row to a session dictionary."""
    meta = _parse_meta(row[3])
    return {
        "id": row[0],
        "content": row[1],
        "created_at": row[2],
        "score_before": meta.get("score_before"),
        "score_after": meta.get("score_after"),
        "delta": meta.get("delta"),
        "actions": meta.get("actions", []),
    }


def _parse_meta(raw: str | None) -> dict[str, Any]:
    """Safely parse JSON metadata from a row."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
