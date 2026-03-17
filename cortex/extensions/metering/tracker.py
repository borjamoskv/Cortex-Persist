"""CORTEX Metering — Usage Tracker.

Records API call consumption per tenant with SQLite-backed counters.
Designed for O(1) inserts and O(1) aggregation via pre-computed monthly buckets.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

__all__ = ["UsageRecord", "UsageTracker"]

logger = logging.getLogger(__name__)

# ─── Schema ──────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    status_code INTEGER NOT NULL DEFAULT 200,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL,
    month_bucket TEXT NOT NULL  -- YYYY-MM for fast aggregation
);

CREATE INDEX IF NOT EXISTS idx_usage_tenant_month
    ON api_usage(tenant_id, month_bucket);

CREATE INDEX IF NOT EXISTS idx_usage_tenant_ts
    ON api_usage(tenant_id, timestamp);

CREATE TABLE IF NOT EXISTS usage_monthly_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    month_bucket TEXT NOT NULL,
    total_calls INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL,
    UNIQUE(tenant_id, month_bucket)
);
"""


class UsageRecord:
    """A single API usage record."""

    __slots__ = (
        "tenant_id",
        "endpoint",
        "method",
        "status_code",
        "tokens_used",
        "timestamp",
    )

    def __init__(
        self,
        tenant_id: str,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        tokens_used: int = 0,
        timestamp: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.tokens_used = tokens_used
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()


class UsageTracker:
    """SQLite-backed API usage tracker.

    Thread-safe via WAL mode. Optimized for high-frequency inserts
    with batched monthly summary updates.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from cortex.config import DB_PATH

            db_path = DB_PATH
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)  # type: ignore[type-error]
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA_SQL)
        return self._conn

    def record(self, record: UsageRecord) -> None:
        """Record a single API call. O(1) insert."""
        conn = self._get_conn()
        now = record.timestamp
        month_bucket = now[:7]  # YYYY-MM

        conn.execute(
            "INSERT INTO api_usage (tenant_id, endpoint, method, status_code, tokens_used, "
            "timestamp, month_bucket) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record.tenant_id,
                record.endpoint,
                record.method,
                record.status_code,
                record.tokens_used,
                now,
                month_bucket,
            ),
        )

        # Upsert monthly summary — atomic O(1)
        conn.execute(
            "INSERT INTO usage_monthly_summary (tenant_id, month_bucket, total_calls, "
            "total_tokens, last_updated) VALUES (?, ?, 1, ?, ?) "
            "ON CONFLICT(tenant_id, month_bucket) DO UPDATE SET "
            "total_calls = total_calls + 1, "
            "total_tokens = total_tokens + excluded.total_tokens, "
            "last_updated = excluded.last_updated",
            (record.tenant_id, month_bucket, record.tokens_used, now),
        )
        conn.commit()

    def get_usage(
        self,
        tenant_id: str,
        month_bucket: str | None = None,
    ) -> dict[str, Any]:
        """Get usage stats for a tenant in a given month.

        Returns:
            {calls_used, tokens_used, month, last_call_at}
        """
        conn = self._get_conn()
        if month_bucket is None:
            month_bucket = datetime.now(timezone.utc).strftime("%Y-%m")

        row = conn.execute(
            "SELECT total_calls, total_tokens, last_updated FROM usage_monthly_summary "
            "WHERE tenant_id = ? AND month_bucket = ?",
            (tenant_id, month_bucket),
        ).fetchone()

        if row:
            return {
                "calls_used": row["total_calls"],
                "tokens_used": row["total_tokens"],
                "month": month_bucket,
                "last_call_at": row["last_updated"],
            }
        return {
            "calls_used": 0,
            "tokens_used": 0,
            "month": month_bucket,
            "last_call_at": None,
        }

    def get_usage_history(
        self,
        tenant_id: str,
        months: int = 12,
    ) -> list[dict[str, Any]]:
        """Get usage history for the last N months."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT month_bucket, total_calls, total_tokens, last_updated "
            "FROM usage_monthly_summary WHERE tenant_id = ? "
            "ORDER BY month_bucket DESC LIMIT ?",
            (tenant_id, months),
        ).fetchall()

        return [
            {
                "month": r["month_bucket"],
                "calls_used": r["total_calls"],
                "tokens_used": r["total_tokens"],
                "last_call_at": r["last_updated"],
            }
            for r in rows
        ]

    def get_endpoint_breakdown(
        self,
        tenant_id: str,
        month_bucket: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get per-endpoint breakdown for a tenant in a month."""
        conn = self._get_conn()
        if month_bucket is None:
            month_bucket = datetime.now(timezone.utc).strftime("%Y-%m")

        rows = conn.execute(
            "SELECT endpoint, method, COUNT(*) as calls, SUM(tokens_used) as tokens "
            "FROM api_usage WHERE tenant_id = ? AND month_bucket = ? "
            "GROUP BY endpoint, method ORDER BY calls DESC",
            (tenant_id, month_bucket),
        ).fetchall()

        return [
            {
                "endpoint": r["endpoint"],
                "method": r["method"],
                "calls": r["calls"],
                "tokens": r["tokens"],
            }
            for r in rows
        ]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> UsageTracker:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def record_call(
        self,
        tenant_id: str,
        endpoint: str,
        *,
        method: str = "GET",
        status_code: int = 200,
        tokens_used: int = 0,
    ) -> None:
        """Convenience wrapper — record a call without constructing UsageRecord."""
        self.record(
            UsageRecord(
                tenant_id=tenant_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                tokens_used=tokens_used,
            )
        )
