"""MEJORAlo Ledger — session recording and history retrieval."""

import json
import logging
from typing import Any

from cortex.engine import CortexEngine
from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN

__all__ = ["record_session", "get_history", "record_scar", "get_scars"]

logger = logging.getLogger("cortex.extensions.mejoralo")

_VERSION = "9.0"


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
        fact_id,
        project,
        delta,
    )
    return fact_id  # type: ignore[reportReturnType]


def get_history(engine: CortexEngine, project: str, limit: int = 20) -> list[dict[str, Any]]:
    """Retrieve past MEJORAlo sessions from the ledger."""
    conn = engine._get_sync_conn()
    try:
        rows = conn.execute(
            f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
            "WHERE f.project = ? AND f.fact_type = 'decision' "
            "AND f.tags LIKE '%mejoralo%' AND f.valid_until IS NULL "
            "ORDER BY f.id DESC LIMIT ?",
            (project, limit),
        ).fetchall()
        facts = [engine._row_to_fact(row, tenant_id=row[1]) for row in rows]
    finally:
        conn.close()

    return [
        {
            "id": f["id"],
            "content": f["content"],
            "created_at": f["created_at"],
            "score_before": f.get("meta", {}).get("score_before"),
            "score_after": f.get("meta", {}).get("score_after"),
            "delta": f.get("meta", {}).get("delta"),
            "actions": f.get("meta", {}).get("actions", []),
        }
        for f in facts
    ]


def record_scar(
    engine: CortexEngine,
    project: str,
    file_path: str,
    error_trace: str,
    diff: str | None = None,
) -> int:
    """Record a failure (Scar) in the CORTEX ledger to prevent future regressions.

    Returns:
        The fact ID of the persisted scar record.
    """
    content = f"MEJORAlo v{_VERSION} SCAR en {file_path}:\n\nError Trace:\n{error_trace}\n\n"
    if diff:
        content += f"AST-Diff causal:\n{diff}"

    fact_id = engine.store_sync(
        project=project,
        content=content,
        fact_type="error",
        tags=["mejoralo", "scar", f"v{_VERSION}"],
        confidence="verified",
        source="cortex-mejoralo",
        meta={
            "file_path": file_path,
            "error_trace": error_trace,
            "version": _VERSION,
        },
    )
    logger.info("Recorded SCAR #%d for %s in %s", fact_id, file_path, project)
    return fact_id  # type: ignore[reportReturnType]


def get_scars(
    engine: CortexEngine, project: str, file_path: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Retrieve past SCARs for a particular file."""
    conn = engine._get_sync_conn()
    try:
        rows = conn.execute(
            f"SELECT {FACT_COLUMNS} {FACT_JOIN} "
            "WHERE f.project = ? AND f.fact_type = 'error' "
            "AND f.tags LIKE '%mejoralo%' AND f.valid_until IS NULL "
            "ORDER BY f.id DESC",
            (project,),
        ).fetchall()
        facts = [engine._row_to_fact(row, tenant_id=row[1]) for row in rows]
    finally:
        conn.close()

    scars = []
    for f in facts:
        if f.get("meta", {}).get("file_path") == file_path:
            scars.append(
                {
                    "id": f["id"],
                    "content": f["content"],
                    "created_at": f["created_at"],
                    "file_path": file_path,
                    "error_trace": f.get("meta", {}).get("error_trace"),
                }
            )
            if len(scars) >= limit:
                break
    return scars


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
