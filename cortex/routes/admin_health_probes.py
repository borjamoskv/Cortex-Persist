"""admin_health_probes — Health probe registry for the Admin router.

Extracted from routes/admin.py to satisfy the Landauer LOC barrier (≤500).
All probes are pure synchronous functions, individually failable without cascading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request

ProbeResult = tuple[str, bool, dict[str, str | int | float]]

# Ledger lag threshold before marking as unhealthy
_LEDGER_LAG_THRESHOLD = 1000


def build_health_probes(
    conn: object,
    request: Request,
    schema_version: str,
) -> dict[str, object]:
    """Build the probe registry for deep health check.

    Each probe returns (status_str, is_healthy, details_dict).
    Probes are designed to be individually failable without cascading.
    """

    def _probe_database() -> ProbeResult:
        conn.execute("SELECT 1").fetchone()  # type: ignore[union-attr]
        return "ok", True, {"detail": "SELECT 1 succeeded"}

    def _probe_schema() -> ProbeResult:
        row = conn.execute(  # type: ignore[union-attr]
            "SELECT value FROM cortex_meta WHERE key = 'schema_version'",
        ).fetchone()
        db_ver = row[0] if row else "unknown"
        if db_ver == schema_version:
            return "ok", True, {"version": db_ver}
        return ("drift", False, {"expected": schema_version, "actual": db_ver})

    def _probe_ledger() -> ProbeResult:
        last_cp = conn.execute(  # type: ignore[union-attr]
            "SELECT MAX(tx_end_id) FROM merkle_roots",
        ).fetchone()
        last_tx = last_cp[0] if last_cp else 0
        pending_row = conn.execute(  # type: ignore[union-attr]
            "SELECT COUNT(*) FROM transactions WHERE id > ?",
            (last_tx,),
        ).fetchone()
        pending = pending_row[0] if pending_row else 0
        healthy = pending < _LEDGER_LAG_THRESHOLD
        return (
            "ok" if healthy else "warning",
            healthy,
            {"pending_uncheckpointed": pending, "last_checkpoint_tx": last_tx},
        )

    def _probe_fts() -> ProbeResult:
        conn.execute("SELECT COUNT(*) FROM episodes_fts").fetchone()  # type: ignore[union-attr]
        return "ok", True, {"detail": "episodes_fts accessible"}

    def _probe_pool() -> ProbeResult:
        pool = request.app.state.pool
        max_c: int = getattr(pool, "max_connections", 0)
        active: int = getattr(pool, "_active_count", 0)
        pct = (active / max_c) * 100 if max_c else 0
        return (
            "ok",
            True,
            {"active_connections": active, "max_connections": max_c, "utilization": f"{pct:.0f}%"},
        )

    def _probe_semantic_memory() -> ProbeResult:
        try:
            total_row = conn.execute("SELECT COUNT(*) FROM facts_meta").fetchone()  # type: ignore[union-attr]
            total = total_row[0] if total_row else 0
            if total == 0:
                return (
                    "ok",
                    True,
                    {"useful_facts_ratio": 0.0, "duplicates_ratio": 0.0, "total_facts": 0},
                )

            useful_row = conn.execute(  # type: ignore[union-attr]
                "SELECT COUNT(*) FROM facts_meta WHERE success_rate > 0"
            ).fetchone()
            useful = useful_row[0] if useful_row else 0

            dup_query = (
                "SELECT SUM(c - 1) FROM ("
                "SELECT content, COUNT(*) as c FROM facts_meta GROUP BY content HAVING c > 1"
                ")"
            )
            dup_rows = conn.execute(dup_query).fetchone()  # type: ignore[union-attr]
            dup_count = dup_rows[0] if dup_rows and dup_rows[0] is not None else 0

            useful_ratio = useful / total
            dup_ratio = dup_count / total
            healthy = dup_ratio < 0.2
            return (
                "ok" if healthy else "warning",
                healthy,
                {
                    "useful_facts_ratio": round(useful_ratio, 3),
                    "duplicates_ratio": round(dup_ratio, 3),
                    "total_facts": total,
                },
            )
        except Exception as e:  # noqa: BLE001 — health probe boundary isolates failures
            return "error", False, {"detail": str(e)}

    return {
        "database": _probe_database,
        "schema": _probe_schema,
        "ledger": _probe_ledger,
        "search_fts": _probe_fts,
        "pool": _probe_pool,
        "semantic_memory": _probe_semantic_memory,
    }
