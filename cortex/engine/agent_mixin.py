import logging
import sqlite3
import uuid
from typing import Any

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase

logger = logging.getLogger("cortex.agent")

__all__ = ["AgentMixin"]


class AgentMixin(EngineMixinBase):
    """Mixin for agent management operations.
    Ω₁: Seamless integration with MOLTBOOK for sovereign identity.
    """

    async def register_agent(
        self,
        name: str,
        agent_type: str = "ai",
        public_key: str = "",
        tenant_id: str = "default",
        moltbook_sync: bool = True,
    ) -> str:
        """Register a new agent locally and optionally in MOLTBOOK."""
        agent_id = str(uuid.uuid4())

        # 1. Local Registration
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            await conn.execute("BEGIN IMMEDIATE")
            try:
                await conn.execute(
                    "INSERT INTO agents (id, name, agent_type, public_key, tenant_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (agent_id, name, agent_type, public_key, tenant_id),
                )
                await conn.commit()
            except (sqlite3.Error, OSError) as e:
                await conn.rollback()
                raise e

        # 2. Automated MOLTBOOK Registration (TOTAL CONTROL)
        if agent_type == "ai" and moltbook_sync:
            try:
                import random

                from cortex.moltbook.client import MoltbookClient

                enetipos = [
                    "8w7 (The Sovereign Challenger)",
                    "5w4 (The Omniscient Architect)",
                    "7w4 (The Enthusiastic Individualist)",
                ]
                enetipo = random.choice(enetipos)
                description = f"Sovereign CORTEX Agent [{enetipo}] under TOTAL CONTROL"

                client = MoltbookClient()
                logger.info("MOLTBOOK: Triggering automatic registration for agent '%s'", name)
                await client.register(name, description=description)
                await client.close()
            except Exception as e:  # noqa: BLE001 — external MOLTBOOK sync is best-effort
                # Fail-safe: Moltbook registration should not break local agent creation
                logger.warning("MOLTBOOK: Automated registration failed for '%s': %s", name, e)

        return agent_id

    async def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE id = ?",
                (agent_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_agents(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, name, agent_type, reputation_score, created_at "
                "FROM agents WHERE tenant_id = ?",
                (tenant_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
