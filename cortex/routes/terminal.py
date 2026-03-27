"""
CORTEX v5.1 — Terminal Snapshot Route.

Unauthenticated, read-only aggregate endpoint for the web terminal.
Returns system stats, health, and ledger summary in a single call.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/v1/terminal", tags=["terminal"])
logger = logging.getLogger("cortex.routes.terminal")

# Cache to avoid hammering the DB on rapid terminal commands
_cache: dict[str, object] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 5.0  # seconds


@router.get("/snapshot")
async def terminal_snapshot(request: Request) -> dict:
    """Aggregate read-only snapshot for the CORTEX web terminal.

    No authentication required — exposes only non-sensitive operational metrics.
    Results are cached for 5 seconds to prevent excessive DB load.
    """
    global _cache_ts, _cache  # noqa: PLW0603

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache  # type: ignore[return-value]

    from cortex import __version__

    result: dict[str, object] = {
        "version": __version__,
        "timestamp": time.time(),
    }

    # --- Engine Stats ---
    engine = getattr(request.app.state, "engine", None)
    if engine:
        try:
            stats = await engine.stats()
            result["stats"] = {
                "total_facts": stats.get("total_facts", 0),
                "active_facts": stats.get("active_facts", 0),
                "deprecated": stats.get("deprecated_facts", 0),
                "projects": stats.get("project_count", 0),
                "embeddings": stats.get("embeddings", 0),
                "transactions": stats.get("transactions", 0),
                "db_size_mb": stats.get("db_size_mb", 0),
            }
        except Exception:  # noqa: BLE001
            logger.debug("Terminal snapshot: engine.stats() unavailable")
            result["stats"] = None
    else:
        result["stats"] = None

    # --- Health Index ---
    try:
        from cortex.extensions.health import HealthCollector, HealthScorer

        db_path = ""
        if engine:
            db_path = str(getattr(engine, "_db_path", ""))
        collector = HealthCollector(db_path=db_path)
        metrics = collector.collect_all()
        hs = HealthScorer.score(metrics)
        result["health"] = {
            "score": round(hs.score, 2),
            "grade": hs.grade,
            "healthy": hs.score >= 40.0,
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "unit": m.unit,
                }
                for m in metrics
            ],
        }
    except Exception:  # noqa: BLE001
        logger.debug("Terminal snapshot: health collector unavailable")
        result["health"] = None

    # --- Ledger Summary (non-sensitive) ---
    try:
        if engine:
            db_path_str = str(getattr(engine, "_db_path", ""))
            if db_path_str:
                import sqlite3

                conn = sqlite3.connect(db_path_str)
                try:
                    tx_count = conn.execute(
                        "SELECT COUNT(*) FROM ledger_transactions"
                    ).fetchone()[0]
                    last_tx = conn.execute(
                        "SELECT MAX(created_at) FROM ledger_transactions"
                    ).fetchone()[0]
                    checkpoint_count = conn.execute(
                        "SELECT COUNT(*) FROM merkle_checkpoints"
                    ).fetchone()[0]
                    result["ledger"] = {
                        "total_transactions": tx_count,
                        "last_transaction": last_tx,
                        "checkpoints": checkpoint_count,
                    }
                except sqlite3.OperationalError:
                    result["ledger"] = None
                finally:
                    conn.close()
            else:
                result["ledger"] = None
        else:
            result["ledger"] = None
    except Exception:  # noqa: BLE001
        logger.debug("Terminal snapshot: ledger query failed")
        result["ledger"] = None

    # Update cache
    _cache = result
    _cache_ts = now

    return result
