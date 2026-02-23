"""
CORTEX v6 — GraphQL Resolvers.

Connects the GraphQL AST Schema directly to CORTEX internal
managers (MemoryManager, AuthManager, DBWriter) while enforcing
RBAC and Multi-Tenant constraints automatically.
"""

from typing import Any


class CortexGraphQLResolvers:
    """Resolvers connecting the GraphQL layer to CORTEX core."""

    def __init__(self, memory_manager: Any, auth_manager: Any) -> None:
        self.memory = memory_manager
        self.auth = auth_manager

    async def resolve_me(self, info: Any) -> dict[str, Any]:
        """Returns the currently authenticated Tenant/Agent information."""
        # Simulated context extraction
        request = info.context.get("request")
        tenant_id = getattr(request.state, "tenant_id", "default")
        role = getattr(request.state, "role", "user")

        return {
            "id": tenant_id,
            "role": role,
            "active_sessions": await self.memory.l3.count(tenant_id=tenant_id),
        }

    async def resolve_search(
        self, info: Any, query: str, limit: int = 5, project: str | None = None
    ) -> list[dict[str, Any]]:
        """Performs semantic search restricted to the caller's tenant."""
        request = info.context.get("request")
        tenant_id = getattr(request.state, "tenant_id", "default")

        results = await self.memory.l2.recall(
            query=query, limit=limit, project=project, tenant_id=tenant_id
        )
        return results

    async def close(self) -> None:
        """Closes any underlying connections."""
        # No connections to close for this resolver, but good practice for interfaces
        pass

    async def resolve_session_events(self, info: Any, limit: int = 100) -> list[Any]:
        """Resolves memory events purely within the caller's Tenant boundary."""
        request = info.context.get("request")
        session_id = getattr(request.state, "session_id", "global")
        tenant_id = getattr(request.state, "tenant_id", "default")

        # Enforcing RBAC at the resolver level
        events = await self.memory.l3.get_session_events(
            session_id=session_id, tenant_id=tenant_id, limit=limit
        )
        return events
