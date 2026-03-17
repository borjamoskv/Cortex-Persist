"""Observatory — consolidated CORTEX system status endpoint.

Provides a single GET /v1/observatory endpoint that aggregates:
- Daemon health (10+ monitors)
- Mejoralo effectiveness trend by project
- Dependency health
- Evolution engine swarm status
- Recent CORTEX decisions
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from cortex.auth import AuthResult, require_permission

__all__ = ["observatory_status"]

logger = logging.getLogger("cortex.routes.observatory")

router = APIRouter(tags=["observatory"])


@router.get("/v1/observatory")
def observatory_status(
    auth: AuthResult = Depends(require_permission("read")),
) -> dict[str, Any]:
    """Consolidated system observatory — one endpoint, full picture."""
    result: dict[str, Any] = {}

    # 1. Daemon status
    result["daemon"] = _get_daemon_status()

    # 2. Dependency health
    result["dependencies"] = _get_dependency_health()

    # 3. Mejoralo effectiveness (per known project)
    result["effectiveness"] = _get_effectiveness()

    # 4. Evolution engine status
    result["evolution"] = _get_evolution_status()

    # 5. Recent decisions
    result["recent_decisions"] = _get_recent_decisions()

    return result


def _get_daemon_status() -> dict[str, Any]:
    """Load last daemon check results."""
    try:
        from cortex.extensions.daemon import MoskvDaemon

        status = MoskvDaemon.load_status()
        return status if status else {"status": "no_data"}
    except (ImportError, RuntimeError, OSError) as e:
        return {"status": "error", "detail": str(e)}


def _get_dependency_health() -> dict[str, Any]:
    """Run dependency health checks."""
    try:
        from cortex.extensions.daemon.monitors.dependency_health import (
            DependencyHealthMonitor,
        )

        monitor = DependencyHealthMonitor()
        return monitor.status()
    except (ImportError, RuntimeError, OSError) as e:
        return {"status": "error", "detail": str(e)}


def _get_effectiveness() -> dict[str, Any]:
    """Get effectiveness trend for known projects."""
    try:
        from cortex.cli.common import get_engine
        from cortex.config import DEFAULT_DB_PATH
        from cortex.extensions.mejoralo.effectiveness import EffectivenessTracker

        engine = get_engine(str(DEFAULT_DB_PATH))
        try:
            tracker = EffectivenessTracker(engine)
            # Get trend for the default 'cortex' project
            trend = tracker.project_trend("cortex")
            return {"cortex": trend.to_dict()}
        finally:
            engine.close_sync()
    except (ImportError, RuntimeError, OSError) as e:
        return {"status": "error", "detail": str(e)}


def _get_evolution_status() -> dict[str, Any]:
    """Get evolution engine swarm status if running."""
    try:
        from cortex.extensions.evolution.engine import EvolutionEngine

        engine = EvolutionEngine(resume=True, persist=False)  # type: ignore[reportCallIssue]
        return engine.swarm_status()  # type: ignore[reportAttributeAccessIssue]
    except (ImportError, RuntimeError, OSError) as e:
        return {"status": "not_running", "detail": str(e)}


def _get_recent_decisions() -> list[dict[str, Any]]:
    """Fetch the 10 most recent CORTEX decisions."""
    try:
        from cortex.cli.common import get_engine
        from cortex.config import DEFAULT_DB_PATH

        engine = get_engine(str(DEFAULT_DB_PATH))
        try:
            conn = engine._get_sync_conn()
            try:
                rows = conn.execute(
                    "SELECT id, project, content, created_at "
                    "FROM facts "
                    "WHERE fact_type = 'decision' AND valid_until IS NULL "
                    "ORDER BY id DESC LIMIT 10"
                ).fetchall()
                return [
                    {
                        "id": r[0],
                        "project": r[1],
                        "content": r[2][:200],
                        "created_at": r[3],
                    }
                    for r in rows
                ]
            finally:
                conn.close()
        finally:
            engine.close_sync()
    except (ImportError, RuntimeError, OSError) as e:
        return [{"status": "error", "detail": str(e)}]
