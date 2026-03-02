"""
CORTEX v5.0 — Tenant Router.

Routes requests to the correct database based on tenant_id.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections import OrderedDict
from typing import Any, Final

from cortex.storage import StorageMode, get_storage_mode

__all__ = ["TenantRouter", "get_router"]

logger = logging.getLogger("cortex.storage.router")

_MAX_BACKENDS: Final[int] = 500


class TenantRouter:
    """Routes tenant requests to the correct storage backend.

    Bounded L1 cache of active connections to prevent FD exhaustion.
    """

    def __init__(self):
        self._mode = get_storage_mode()
        self._connections: OrderedDict[str, Any] = OrderedDict()
        self._base_url = os.environ.get("TURSO_DATABASE_URL", "")
        self._auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
        self._postgres_dsn = os.environ.get("POSTGRES_DSN", "")

    async def get_backend(self, tenant_id: str = "default", content: str | None = None):
        """Get the storage backend for a specific tenant.

        If sensitive content is detected, it FORCES local storage to prevent
        leaks to the cloud (Zero-Trust Privacy).

        Args:
            tenant_id: The tenant identifier from auth.
            content: Optional string content to analyze for sensitivity.

        Returns:
            A StorageBackend instance connected to the tenant's database.
        """
        # Zero-Trust Check: Force local if secrets detected
        if content:
            from cortex.storage.classifier import classify_content

            sensitivity = classify_content(content)
            if sensitivity.is_sensitive:
                logger.warning(
                    "PRIVACY ALERT: Sensitive patterns detected (%s). "
                    "Forcing LOCAL storage for tenant [%s].",
                    ", ".join(sensitivity.matches),
                    tenant_id,
                )
                return await self._get_local_backend()

        if self._mode == StorageMode.LOCAL:
            return await self._get_local_backend()

        if self._mode == StorageMode.POSTGRES:
            return await self._get_postgres_backend(tenant_id)

        backend = await self._get_turso_backend(tenant_id)
        
        # Connection Eviction (Axiom Ω₂)
        if len(self._connections) > _MAX_BACKENDS:
            # Pop the oldest connection (LRU)
            old_tenant, old_conn = self._connections.popitem(last=False)
            try:
                await old_conn.close()
                logger.debug("Evicted backend connection for tenant: %s", old_tenant)
            except Exception as e:
                logger.warning("Error closing evicted tenant %s: %s", old_tenant, e)
        
        return backend

    async def _get_local_backend(self):
        """Return the shared local SQLite connection pool."""
        if "local" not in self._connections:
            from cortex.config import DB_PATH
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(str(DB_PATH))
            await pool.initialize()
            self._connections["local"] = pool
            logger.info("Local storage initialized at %s", DB_PATH)

        return self._connections["local"]

    async def _get_turso_backend(self, tenant_id: str):
        """Get or create a Turso connection for this tenant."""
        if tenant_id in self._connections:
            # Health check existing connection
            conn = self._connections[tenant_id]
            if await conn.health_check():
                return conn

            logger.warning("Turso connection unhealthy for %s, reconnecting", tenant_id)
            await conn.close()

        from cortex.storage.turso import TursoBackend

        url = TursoBackend.tenant_db_url(self._base_url, tenant_id)
        backend = TursoBackend(url=url, auth_token=self._auth_token)
        await backend.connect()

        self._connections[tenant_id] = backend
        logger.info("Turso backend connected for tenant: %s → %s", tenant_id, url)
        return backend

    async def _get_postgres_backend(self, tenant_id: str):
        """Get or create a PostgreSQL connection for this tenant.

        All tenants share the same PostgreSQL database + pool,
        isolated by tenant_id column (shared schema, not separate DBs).
        """
        cache_key = "postgres"
        if cache_key in self._connections:
            conn = self._connections[cache_key]
            if await conn.health_check():
                return conn

            logger.warning("PostgreSQL pool unhealthy, reconnecting")
            await conn.close()

        from cortex.storage.postgres import PostgresBackend

        if not self._postgres_dsn:
            raise RuntimeError(
                "POSTGRES_DSN is required when CORTEX_STORAGE=postgres. "
                "Example: postgresql://user:pass@host:5432/cortex"
            )

        backend = PostgresBackend(dsn=self._postgres_dsn)
        await backend.connect()

        self._connections[cache_key] = backend
        logger.info(
            "PostgreSQL backend connected for tenant: %s",
            tenant_id,
        )
        return backend

    async def close_all(self) -> None:
        """Close all tenant connections (for shutdown)."""
        for tenant_id, conn in self._connections.items():
            try:
                await conn.close()
                logger.info("Closed connection for tenant: %s", tenant_id)
            except (sqlite3.Error, OSError) as e:
                logger.warning("Error closing tenant %s: %s", tenant_id, e)
        self._connections.clear()

    @property
    def mode(self) -> StorageMode:
        return self._mode

    @property
    def active_tenants(self) -> list[str]:
        return list(self._connections.keys())

    def __repr__(self) -> str:
        return f"TenantRouter(mode={self._mode.value}, active_tenants={len(self._connections)})"


# ─── Singleton ────────────────────────────────────────────────────────

_router: TenantRouter | None = None


def get_router() -> TenantRouter:
    """Get the global tenant router singleton."""
    global _router
    if _router is None:
        _router = TenantRouter()
    return _router
