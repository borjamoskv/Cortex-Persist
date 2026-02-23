"""CORTEX ADK Tools — Bridge between ADK agents and CortexEngine.

Wraps CortexEngine operations as plain Python functions that ADK agents
can call as tools. Optimized for low-latency autonomous operations.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from cortex.engine import CortexEngine

__all__ = [
    "ALL_TOOLS",
    "adk_deprecate",
    "adk_ledger_verify",
    "adk_search",
    "adk_status",
    "adk_store",
]

logger = logging.getLogger("cortex.adk.tools")

_DEFAULT_DB = os.path.expanduser("~/.cortex/cortex.db")


def _get_db_path() -> str:
    """Resolve the active CORTEX database path."""
    return os.environ.get("CORTEX_DB_PATH", _DEFAULT_DB)


@contextmanager
def _sovereign_engine() -> Generator[CortexEngine, None, None]:
    """Scoped context manager for CORTEX engine operations."""
    path = _get_db_path()
    engine = CortexEngine(path, auto_embed=False)
    try:
        engine.init_db()
        yield engine
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("Sovereign Tool Failure: %s", exc)
        raise
    finally:
        engine.close()


# ─── Store ────────────────────────────────────────────────────────────


def adk_store(
    project: str,
    content: str,
    fact_type: str = "knowledge",
    tags: str = "[]",
    source: str = "",
) -> dict[str, Any]:
    """
    Store a fact in CORTEX sovereign memory.

    Args:
        project: Project namespace (e.g. 'cortex', 'naroa-2026').
        content: The fact content to store.
        fact_type: One of: knowledge, decision, error, rule, axiom, schema, idea, ghost, bridge.
        tags: JSON array of string tags (e.g. '["architecture", "adk"]').
        source: Optional source attribution.

    Returns:
        A dict with status and fact_id.
    """
    try:
        parsed_tags = json.loads(tags) if tags else []
    except (json.JSONDecodeError, TypeError):
        parsed_tags = []

    try:
        with _sovereign_engine() as engine:
            fact_id = engine.store(
                project=project,
                content=content,
                fact_type=fact_type,
                tags=parsed_tags,
                confidence="stated",
                source=source or None,
            )
            return {"status": "success", "fact_id": fact_id, "project": project}
    except Exception as exc:
        return {"status": "error", "message": f"Store failed: {exc}"}


# ─── Search ───────────────────────────────────────────────────────────


def adk_search(
    query: str,
    project: str = "",
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search CORTEX memory using hybrid semantic + text search.

    Args:
        query: Natural language search query.
        project: Optional project filter.
        top_k: Number of results to return (1-20).

    Returns:
        A dict with status and results list.
    """
    try:
        with _sovereign_engine() as engine:
            results = engine.search(
                query=query,
                project=project or None,
                top_k=min(max(top_k, 1), 20),
            )

            if not results:
                return {"status": "success", "results": [], "message": "No results found."}

            formatted = [
                {
                    "fact_id": r.fact_id,
                    "score": round(r.score, 3),
                    "project": r.project,
                    "fact_type": r.fact_type,
                    "content": r.content,
                }
                for r in results
            ]

            return {"status": "success", "results": formatted, "count": len(formatted)}
    except Exception as exc:
        return {"status": "error", "message": f"Search failed: {exc}"}


# ─── Status ───────────────────────────────────────────────────────────


def adk_status() -> dict[str, Any]:
    """
    Get CORTEX system status and statistics.

    Returns:
        A dict with system stats including fact counts, projects, and DB size.
    """
    try:
        with _sovereign_engine() as engine:
            stats = engine.stats()
            return {"status": "success", **stats}
    except Exception as exc:
        return {"status": "error", "message": f"Status retrieval failed: {exc}"}


# ─── Ledger Verify ────────────────────────────────────────────────────


def adk_ledger_verify() -> dict[str, Any]:
    """
    Verify the integrity of the CORTEX immutable transaction ledger.

    Performs a full hash-chain verification and Merkle checkpoint audit.

    Returns:
        A dict with verification results.
    """
    from cortex.engine.ledger import ImmutableLedger

    try:
        with _sovereign_engine() as engine:
            ledger = ImmutableLedger(engine._conn)
            report = ledger.verify_integrity()
            return {
                "status": "success",
                "valid": report.get("valid", False),
                "transactions_checked": report.get("tx_checked", 0),
                "roots_checked": report.get("roots_checked", 0),
                "violations": report.get("violations", []),
            }
    except Exception as exc:
        return {"status": "error", "message": f"Ledger verification failed: {exc}"}


# ─── Deprecate ────────────────────────────────────────────────────────


def adk_deprecate(
    fact_id: int,
    reason: str = "",
) -> dict[str, Any]:
    """
    Deprecate a fact in CORTEX memory.

    Marks a fact as deprecated so it no longer appears in searches.
    The fact is retained for audit purposes but hidden from active queries.

    Args:
        fact_id: The numeric ID of the fact to deprecate.
        reason: Optional reason for deprecation.

    Returns:
        A dict with status and the deprecated fact ID.
    """
    try:
        with _sovereign_engine() as engine:
            engine.deprecate(fact_id, reason=reason or None)
            return {"status": "success", "fact_id": fact_id, "deprecated": True}
    except Exception as exc:
        return {"status": "error", "message": f"Deprecation failed: {exc}"}


# ─── Tool Registry ────────────────────────────────────────────────────

ALL_TOOLS = [adk_store, adk_search, adk_status, adk_ledger_verify, adk_deprecate]
"""All available CORTEX tools for ADK agents."""
