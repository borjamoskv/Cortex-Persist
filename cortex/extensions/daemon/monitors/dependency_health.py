"""Dependency Health Monitor — checks external service availability.

Pluggable health checks for CORTEX dependencies:
- SQLite (always present)
- PostgreSQL (optional, v6 Cloud)
- Qdrant (optional, v6 Cloud)
- Redis (optional, v6 Cloud)
- Embedding model (optional)

Each check is Optional — if the service isn't configured, it's skipped.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

__all__ = ["DependencyHealthMonitor", "DependencyAlert"]

logger = logging.getLogger("cortex.extensions.daemon.dependency_health")


@dataclass
class DependencyAlert:
    """Alert for a dependency that is unavailable or degraded."""

    service: str
    status: str  # "unavailable", "degraded", "timeout"
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"service": self.service, "status": self.status, "detail": self.detail}


@dataclass
class HealthCheck:
    """Base for pluggable health checks."""

    name: str
    enabled: bool = True

    def check(self) -> DependencyAlert | None:
        """Return an alert if unhealthy, None if OK."""
        raise NotImplementedError


class SQLiteHealthCheck(HealthCheck):
    """Verify SQLite database is accessible and not corrupt."""

    def __init__(self, db_path: str | None = None):
        super().__init__(name="sqlite")
        from cortex.config import DEFAULT_DB_PATH

        self.db_path = db_path or str(DEFAULT_DB_PATH)

    def check(self) -> DependencyAlert | None:
        import sqlite3
        from pathlib import Path

        if not Path(self.db_path).exists():
            return DependencyAlert("sqlite", "unavailable", f"DB not found: {self.db_path}")
        try:
            from cortex.database.core import connect as db_connect

            conn = db_connect(self.db_path, timeout=2)
            conn.execute("SELECT 1")
            conn.close()
            return None
        except sqlite3.Error as e:
            return DependencyAlert("sqlite", "degraded", str(e))


class PostgreSQLHealthCheck(HealthCheck):
    """Check PostgreSQL connectivity (only if configured)."""

    def __init__(self):
        super().__init__(name="postgresql")
        self.dsn = os.environ.get("CORTEX_PG_DSN", "")
        self.enabled = bool(self.dsn)

    def check(self) -> DependencyAlert | None:
        if not self.enabled:
            return None
        try:
            import psycopg2  # type: ignore[import-untyped]

            conn = psycopg2.connect(self.dsn, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return None
        except ImportError:
            return DependencyAlert("postgresql", "unavailable", "psycopg2 not installed")
        except Exception as e:  # noqa: BLE001
            return DependencyAlert("postgresql", "unavailable", str(e))


class QdrantHealthCheck(HealthCheck):
    """Check Qdrant vector store connectivity (only if configured)."""

    def __init__(self):
        super().__init__(name="qdrant")
        self.url = os.environ.get("CORTEX_QDRANT_URL", "")
        self.enabled = bool(self.url)

    def check(self) -> DependencyAlert | None:
        if not self.enabled:
            return None
        try:
            import httpx

            resp = httpx.get(f"{self.url}/healthz", timeout=3)
            if resp.status_code != 200:
                return DependencyAlert("qdrant", "degraded", f"HTTP {resp.status_code}")
            return None
        except Exception as e:  # noqa: BLE001
            return DependencyAlert("qdrant", "unavailable", str(e))


class RedisHealthCheck(HealthCheck):
    """Check Redis connectivity (only if configured)."""

    def __init__(self):
        super().__init__(name="redis")
        self.url = os.environ.get("CORTEX_REDIS_URL", "")
        self.enabled = bool(self.url)

    def check(self) -> DependencyAlert | None:
        if not self.enabled:
            return None
        try:
            import redis  # type: ignore[import-untyped]

            client = redis.from_url(self.url, socket_timeout=3)
            client.ping()
            return None
        except ImportError:
            return DependencyAlert("redis", "unavailable", "redis-py not installed")
        except Exception as e:  # noqa: BLE001
            return DependencyAlert("redis", "unavailable", str(e))


class EmbeddingModelHealthCheck(HealthCheck):
    """Verify the embedding model is loadable."""

    def __init__(self):
        super().__init__(name="embedding_model")

    def check(self) -> DependencyAlert | None:
        try:
            from cortex.embeddings.manager import EmbeddingManager

            provider = EmbeddingManager(engine=None)
            # Quick sanity check
            vec = provider.embed("test")
            if vec is None or len(vec) == 0:
                return DependencyAlert("embedding_model", "degraded", "Empty embedding returned")
            return None
        except (ImportError, RuntimeError, OSError) as e:
            return DependencyAlert("embedding_model", "unavailable", str(e))


class DependencyHealthMonitor:
    """Orchestrates pluggable dependency health checks.

    Usage:
        monitor = DependencyHealthMonitor()
        alerts = monitor.check()
        # alerts is empty if all dependencies are healthy
    """

    def __init__(
        self,
        db_path: str | None = None,
        extra_checks: list[HealthCheck] | None = None,
    ):
        self.checks: list[HealthCheck] = [
            SQLiteHealthCheck(db_path),
            PostgreSQLHealthCheck(),
            QdrantHealthCheck(),
            RedisHealthCheck(),
            EmbeddingModelHealthCheck(),
        ]
        if extra_checks:
            self.checks.extend(extra_checks)

    def check(self) -> list[DependencyAlert]:
        """Run all enabled health checks. Returns list of alerts."""
        alerts: list[DependencyAlert] = []
        for health_check in self.checks:
            if not health_check.enabled:
                continue
            try:
                alert = health_check.check()
                if alert is not None:
                    alerts.append(alert)
                    logger.warning(
                        "Dependency unhealthy: %s — %s: %s",
                        alert.service,
                        alert.status,
                        alert.detail,
                    )
            except Exception as e:  # noqa: BLE001
                alerts.append(DependencyAlert(health_check.name, "error", f"Check crashed: {e}"))
        return alerts

    def status(self) -> dict[str, Any]:
        """Return full dependency health status as dict."""
        results: dict[str, Any] = {}
        for health_check in self.checks:
            if not health_check.enabled:
                results[health_check.name] = {"status": "not_configured"}
                continue
            try:
                alert = health_check.check()
                if alert is None:
                    results[health_check.name] = {"status": "healthy"}
                else:
                    results[health_check.name] = alert.to_dict()
            except Exception as e:  # noqa: BLE001
                results[health_check.name] = {"status": "error", "detail": str(e)}
        return results
