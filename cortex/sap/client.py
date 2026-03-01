"""CORTEX v5.0 — SAP OData Client.

Async HTTP facade for SAP OData V2 services.
Provides entity CRUD via underlying Transport and Vault isolation.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = [
    "SAPAuthError",
    "SAPClient",
    "SAPConfig",
    "SAPConnectionError",
    "SAPEntityError",
]

logger = logging.getLogger("cortex.sap.client")

# Re-export from models for backwards compatibility
from cortex.sap.models import (  # noqa: E402
    SAPAuthError,
    SAPConfig,
    SAPConnectionError,
    SAPEntityError,
)
from cortex.sap.schema import parse_metadata_xml  # noqa: E402
from cortex.sap.transport import SAPTransport  # noqa: E402
from cortex.sap.vault import SAPVault  # noqa: E402

# ─── Client ──────────────────────────────────────────────────────────


class SAPClient:
    """Async SAP OData V2 facade.

    Delegates HTTP connection lifecycle to SAPTransport and
    auth tokens to SAPVault. Focuses purely on semantic Entity CRUD.
    """

    def __init__(self, config: SAPConfig) -> None:
        self.config = config
        self.vault = SAPVault(config)
        self.transport = SAPTransport(config, self.vault)

    async def connect(self) -> dict[str, Any]:
        """Establish connection and negotiate CSRF via transport.

        Returns:
            dict with 'status' and 'csrf' keys.
        """
        await self.transport.connect()
        return {"status": "connected", "csrf": self.vault.has_csrf}

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        await self.transport.close()

    # ─── Entity Operations ───────────────────────────────────────────

    async def read_entity_set(
        self,
        entity_set: str,
        *,
        filters: str | None = None,
        select: list[str] | None = None,
        expand: list[str] | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Read entities from an OData entity set."""
        params: dict[str, str] = {
            "$format": "json",
            "$top": str(top),
            "$skip": str(skip),
        }
        if filters:
            params["$filter"] = filters
        if select:
            params["$select"] = ",".join(select)
        if expand:
            params["$expand"] = ",".join(expand)

        url = f"{self.config.base_url_normalized}/{entity_set}"
        data = await self.transport.request("GET", url, params=params)

        results = data.get("d", {})
        if isinstance(results, dict):
            return results.get("results", [])
        return []

    async def read_entity(self, entity_set: str, key: str) -> dict[str, Any]:
        """Read a single entity by key."""
        url = f"{self.config.base_url_normalized}/{entity_set}({key})"
        data = await self.transport.request("GET", url, params={"$format": "json"})
        return data.get("d", {})

    async def create_entity(self, entity_set: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity in SAP."""
        url = f"{self.config.base_url_normalized}/{entity_set}"
        result = await self.transport.request("POST", url, json_data=data)
        return result.get("d", result)

    async def update_entity(
        self,
        entity_set: str,
        key: str,
        data: dict[str, Any],
        *,
        merge: bool = True,
    ) -> bool:
        """Update an existing entity."""
        url = f"{self.config.base_url_normalized}/{entity_set}({key})"
        method = "PATCH" if merge else "PUT"
        await self.transport.request(method, url, json_data=data)
        return True

    async def metadata(self) -> dict[str, list[str]]:
        """Fetch service $metadata and parse entity types."""
        url = f"{self.config.base_url_normalized}/$metadata"
        resp = await self.transport.raw_request("GET", url)
        return parse_metadata_xml(resp.text)

    async def health_check(self) -> dict[str, Any]:
        """Check SAP connectivity and return status."""
        try:
            await self.connect()
            return {
                "status": "healthy",
                "base_url": self.config.base_url_normalized,
                "csrf_available": self.vault.has_csrf,
                "auth_type": self.config.auth_type,
            }
        except (SAPConnectionError, SAPAuthError) as e:
            return {
                "status": "unhealthy",
                "base_url": self.config.base_url_normalized,
                "error": str(e),
            }
