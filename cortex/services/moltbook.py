"""
Moltbook Service (MoltService-Ω) — Public API Interface.

Provides the CORTEX-native gateway to Moltbook. 
Follows Ω₆: Decoupled execution. 
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.moltbook.engine import MoltbookEngine

logger = logging.getLogger("cortex.services.moltbook")


class MoltbookService:
    """Sovereign service for Moltbook interactions.
    
    Acts as the bridge between CORTEX core (Agents, CLI) and the 
    Moltbook extension implementation.
    """

    def __init__(self, engine: MoltbookEngine | None = None):
        self._engine = engine
        self._registry_path: str | None = None

    def _get_engine(self) -> MoltbookEngine:
        """Lazy initialization of the extension engine."""
        if self._engine is None:
            # In a full CORTEX init, registry/client config 
            # would be pulled from system settings.
            self._engine = MoltbookEngine()
        return self._engine

    async def register_agent(
        self, 
        name: str, 
        role: str = "analyst", 
        description: str = ""
    ) -> dict[str, Any]:
        """Register a new agent into the Moltbook ecosystem."""
        engine = self._get_engine()
        return await engine.register_agent(name, role, description)

    async def get_status(self) -> dict[str, Any]:
        """Retrieve current Moltbook account and swarm status."""
        engine = self._get_engine()
        return await engine.get_system_status()

    async def run_maintenance(self) -> dict[str, Any]:
        """Run heartbeat/pulse cycles."""
        engine = self._get_engine()
        return await engine.pulse()

    async def search(self, query: str, search_type: str = "all", limit: int = 10) -> dict[str, Any]:
        """Search across Moltbook."""
        engine = self._get_engine()
        return await engine.search(query, search_type=search_type, limit=limit)

    async def get_feed(self, sort: str = "hot", limit: int = 15) -> dict[str, Any]:
        """Get Moltbook feed."""
        engine = self._get_engine()
        return await engine.get_feed(sort=sort, limit=limit)

    async def create_post(self, submolt: str, title: str, content: str = "") -> dict[str, Any]:
        """Create a verified post."""
        engine = self._get_engine()
        return await engine.create_verified_post(submolt, title, content)

    async def list_registered_agents(self) -> list[dict[str, Any]]:
        """List agents in the local Moltbook registry."""
        engine = self._get_engine()
        return engine.registry.get_all_agents()

    async def close(self):
        """Cleanup session."""
        if self._engine is not None:
            await self._engine.close()
