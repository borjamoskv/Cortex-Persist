"""CORTEX ADK Tools — Bridge between ADK agents and CortexEngine.

Wraps CortexEngine operations as plain Python functions that ADK agents
can call as tools. Optimized for low-latency autonomous operations.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import sqlite3
from collections.abc import Awaitable, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, TypeVar, cast

from cortex.engine import CortexEngine

__all__ = [
    "ALL_TOOLS",
    "adk_deprecate",
    "adk_ledger_verify",
    "adk_search",
    "adk_status",
    "adk_store",
]

logger = logging.getLogger("cortex.extensions.adk.tools")

_DEFAULT_DB: Final = str(Path("~/.cortex/cortex.db").expanduser())
_T = TypeVar("_T")


def _get_db_path() -> str:
    """Resolve the active CORTEX database path."""
    import os

    return os.environ.get("CORTEX_DB", os.environ.get("CORTEX_DB_PATH", _DEFAULT_DB))


def _validate_tenant_id(tenant_id: str) -> str:
    """Normalize the tenant boundary used by ADK tool calls."""
    if not isinstance(tenant_id, str):
        raise ValueError("tenant_id must be a non-empty string")
    resolved = tenant_id.strip()
    if not resolved:
        raise ValueError("tenant_id must be a non-empty string")
    return resolved


def _parse_tags(tags: str) -> list[str]:
    """Parse an ADK JSON tag payload into a bounded list of strings."""
    if not tags:
        return []
    try:
        parsed = json.loads(tags)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [tag for tag in parsed if isinstance(tag, str)]


async def _await_value(awaitable: Awaitable[_T]) -> _T:
    return await awaitable


def _run_awaitable(awaitable: Awaitable[_T]) -> _T:
    """Run an awaitable from a synchronous ADK tool, even inside an active loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_await_value(awaitable))

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="cortex-adk-tool") as executor:
        return executor.submit(lambda: asyncio.run(_await_value(awaitable))).result()


def _resolve_engine_result(engine: Any, value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value

    runner = getattr(engine, "_run_sync", None)
    if callable(runner):
        return runner(value)
    return _run_awaitable(cast(Awaitable[Any], value))


def _run_engine_method(engine: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    """Call a CortexEngine method through its sync wrapper when one exists."""
    sync_method = getattr(engine, f"{method_name}_sync", None)
    if callable(sync_method):
        return sync_method(*args, **kwargs)

    method = getattr(engine, method_name, None)
    if not callable(method):
        raise RuntimeError(f"CortexEngine method unavailable: {method_name}")
    return _resolve_engine_result(engine, method(*args, **kwargs))


@contextmanager
def _sovereign_engine() -> Generator[CortexEngine, None, None]:
    """Scoped context manager for CORTEX engine operations."""
    path = _get_db_path()
    engine = CortexEngine(path, auto_embed=False)
    try:
        _run_engine_method(engine, "init_db")
        yield engine
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("Sovereign Tool Failure: %s", exc)
        raise
    finally:
        try:
            _run_engine_method(engine, "close")
        except (sqlite3.Error, OSError, RuntimeError) as exc:
            logger.warning("Sovereign Tool close failed: %s", exc)


# ─── Store ────────────────────────────────────────────────────────────


def adk_store(
    project: str,
    content: str,
    fact_type: str = "knowledge",
    tags: str = "[]",
    source: str = "",
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Store a fact in CORTEX sovereign memory.

    Args:
        project: Project namespace (e.g. 'cortex', 'naroa-2026').
        content: The fact content to store.
        fact_type: One of: knowledge, decision, error, rule, axiom, schema, idea, ghost, bridge.
        tags: JSON array of string tags (e.g. '["architecture", "adk"]').
        source: Optional source attribution.
        tenant_id: Tenant namespace to isolate the write path.

    Returns:
        A dict with status and fact_id.
    """
    try:
        resolved_tenant_id = _validate_tenant_id(tenant_id)
        parsed_tags = _parse_tags(tags)
        with _sovereign_engine() as engine:
            fact_id = _run_engine_method(
                engine,
                "store",
                project=project,
                content=content,
                fact_type=fact_type,
                tags=parsed_tags,
                confidence="stated",
                source=source or None,
                tenant_id=resolved_tenant_id,
            )
            return {
                "status": "success",
                "fact_id": fact_id,
                "project": project,
                "tenant_id": resolved_tenant_id,
            }
    except (sqlite3.Error, ValueError, RuntimeError, OSError) as exc:
        return {"status": "error", "message": f"Store failed: {exc}"}


# ─── Search ───────────────────────────────────────────────────────────


def adk_search(
    query: str,
    project: str = "",
    top_k: int = 5,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Search CORTEX memory using hybrid semantic + text search.

    Args:
        query: Natural language search query.
        project: Optional project filter.
        top_k: Number of results to return (1-20).
        tenant_id: Tenant namespace to isolate the read path.

    Returns:
        A dict with status and results list.
    """
    try:
        resolved_tenant_id = _validate_tenant_id(tenant_id)
        with _sovereign_engine() as engine:
            results = _run_engine_method(
                engine,
                "search",
                query=query,
                project=project or None,
                top_k=min(max(top_k, 1), 20),
                tenant_id=resolved_tenant_id,
            )

            if not results:
                return {
                    "status": "success",
                    "results": [],
                    "message": "No results found.",
                    "tenant_id": resolved_tenant_id,
                }

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

            return {
                "status": "success",
                "results": formatted,
                "count": len(formatted),
                "tenant_id": resolved_tenant_id,
            }
    except (sqlite3.Error, ValueError, RuntimeError, OSError) as exc:
        return {"status": "error", "message": f"Search failed: {exc}"}


# ─── Status ───────────────────────────────────────────────────────────


def adk_status(tenant_id: str = "default") -> dict[str, Any]:
    """
    Get CORTEX system status and statistics.

    Args:
        tenant_id: Tenant namespace for scoped statistics.

    Returns:
        A dict with system stats including fact counts, projects, and DB size.
    """
    try:
        resolved_tenant_id = _validate_tenant_id(tenant_id)
        with _sovereign_engine() as engine:
            stats = _run_engine_method(engine, "stats", tenant_id=resolved_tenant_id)
            return {"status": "success", "tenant_id": resolved_tenant_id, **stats}
    except (sqlite3.Error, ValueError, RuntimeError, OSError) as exc:
        return {"status": "error", "message": f"Status retrieval failed: {exc}"}


# ─── Ledger Verify ────────────────────────────────────────────────────


def adk_ledger_verify(tenant_id: str = "default") -> dict[str, Any]:
    """
    Verify the integrity of the CORTEX immutable transaction ledger.

    Performs a full hash-chain verification and Merkle checkpoint audit.

    Args:
        tenant_id: Tenant namespace for scoped ledger verification.

    Returns:
        A dict with verification results.
    """
    try:
        resolved_tenant_id = _validate_tenant_id(tenant_id)
        with _sovereign_engine() as engine:
            report = _run_engine_method(engine, "verify_ledger", tenant_id=resolved_tenant_id)
            return {
                "status": "success",
                "tenant_id": resolved_tenant_id,
                "valid": report.get("valid", False),
                "transactions_checked": report.get("tx_checked", 0),
                "roots_checked": report.get("roots_checked", 0),
                "violations": report.get("violations", []),
            }
    except (sqlite3.Error, ValueError, RuntimeError, OSError) as exc:
        return {"status": "error", "message": f"Ledger verification failed: {exc}"}


# ─── Deprecate ────────────────────────────────────────────────────────


def adk_deprecate(
    fact_id: int,
    reason: str = "",
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Deprecate a fact in CORTEX memory.

    Marks a fact as deprecated so it no longer appears in searches.
    The fact is retained for audit purposes but hidden from active queries.

    Args:
        fact_id: The numeric ID of the fact to deprecate.
        reason: Optional reason for deprecation.
        tenant_id: Tenant namespace that owns the fact.

    Returns:
        A dict with status and the deprecated fact ID.
    """
    try:
        resolved_tenant_id = _validate_tenant_id(tenant_id)
        with _sovereign_engine() as engine:
            deprecated = bool(
                _run_engine_method(
                    engine,
                    "deprecate",
                    fact_id,
                    reason=reason or None,
                    tenant_id=resolved_tenant_id,
                )
            )
            if not deprecated:
                return {
                    "status": "error",
                    "message": "Fact not found for requested tenant.",
                    "fact_id": fact_id,
                    "tenant_id": resolved_tenant_id,
                }
            return {
                "status": "success",
                "fact_id": fact_id,
                "deprecated": True,
                "tenant_id": resolved_tenant_id,
            }
    except (sqlite3.Error, ValueError, RuntimeError, OSError) as exc:
        return {"status": "error", "message": f"Deprecation failed: {exc}"}


# ─── Tool Registry ────────────────────────────────────────────────────

ALL_TOOLS = [adk_store, adk_search, adk_status, adk_ledger_verify, adk_deprecate]
"""All available CORTEX tools for ADK agents."""
