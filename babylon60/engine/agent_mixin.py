# [C5-REAL] Exergy-Maximized
import logging
import sqlite3
import uuid
from collections.abc import Callable
from typing import Any

import aiosqlite

from babylon60.engine.mixins.base import EngineMixinBase

logger = logging.getLogger("babylon60.extensions.agent")

__all__ = ["AgentMixin"]


def _get_raw_conn(engine: Any) -> object:
    """Isolate private access to engine's raw connection."""
    return engine._get_sync_conn()


def build_health_probes(
    conn: Any, request: Any, schema_version: str
) -> dict[str, Callable[[], tuple[str, bool, dict[str, Any]]]]:
    """Placeholder for health probe logic."""
    return {}


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

                from babylon60.extensions.moltbook.client import MoltbookClient

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
            except (ValueError, RuntimeError, OSError) as e:
                # Fail-safe: Moltbook registration should not break local agent creation
                logger.warning("MOLTBOOK: Automated registration failed for '%s': %s", name, e)

        return agent_id

    async def get_agent(self, agent_id: str, tenant_id: str = "default") -> dict[str, Any] | None:
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, name, agent_type, reputation_score, created_at "
                "FROM agents WHERE id = ? AND tenant_id = ?",
                (agent_id, tenant_id),
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

    async def record_task_eroi(
        self,
        agent_id: str,
        task_type: str,
        exergy_yield: float,
        entropy_paid: float,
        tokens_spent: int = 0,
        status: str = "SUCCESS",
        tenant_id: str = "default",
    ) -> float:
        """Record task EROI and adjust the agent's reputation accordingly."""
        eroi_score = exergy_yield / (entropy_paid + 1.0)
        
        # Calculate reputation delta
        if status == "SUCCESS":
            delta = min(0.10, 0.02 * eroi_score)
        else:
            delta = -max(0.05, min(0.25, 0.10 * entropy_paid))
            
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            await conn.execute("BEGIN IMMEDIATE")
            try:
                # 1. Fetch old reputation
                async with conn.execute(
                    "SELECT reputation_score FROM agents WHERE id = ? AND tenant_id = ?",
                    (agent_id, tenant_id),
                ) as cursor:
                    row = await cursor.fetchone()
                
                if row:
                    old_rep = row[0]
                    new_rep = max(0.0, min(1.0, old_rep + delta))
                    await conn.execute(
                        "UPDATE agents SET reputation_score = ?, updated_at = datetime('now') "
                        "WHERE id = ? AND tenant_id = ?",
                        (new_rep, agent_id, tenant_id),
                    )
                else:
                    initial_rep = 0.5
                    new_rep = max(0.0, min(1.0, initial_rep + delta))
                    await conn.execute(
                        "INSERT INTO agents (id, name, agent_type, reputation_score, public_key, tenant_id) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (agent_id, agent_id.capitalize(), "ai", new_rep, "", tenant_id),
                    )
                
                # 2. Insert EROI record
                await conn.execute(
                    "INSERT INTO agent_tasks_eroi (agent_id, task_type, exergy_yield, entropy_paid, tokens_spent, eroi_score, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (agent_id, task_type, exergy_yield, entropy_paid, tokens_spent, eroi_score, status),
                )
                await conn.commit()
                return new_rep
            except Exception as e:
                await conn.rollback()
                raise e

    async def select_best_agent_for_task(
        self,
        task_type: str,
        candidate_agent_ids: list[str],
        tenant_id: str = "default",
    ) -> str | None:
        """Select the agent with the highest average EROI score for the task type.
        
        Falls back to overall reputation_score if no history exists.
        """
        if not candidate_agent_ids:
            return None
            
        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            # Query average eroi for each candidate
            placeholders = ",".join("?" for _ in candidate_agent_ids)
            query = f"""
                SELECT agent_id, AVG(eroi_score) as avg_eroi
                FROM agent_tasks_eroi
                WHERE task_type = ? AND agent_id IN ({placeholders})
                GROUP BY agent_id
            """
            params = [task_type] + candidate_agent_ids
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                eroi_map = {row[0]: row[1] for row in rows}
                
            # For candidates with no EROI history, fetch their overall reputation_score
            missing_candidates = [cid for cid in candidate_agent_ids if cid not in eroi_map]
            if missing_candidates:
                placeholders_missing = ",".join("?" for _ in missing_candidates)
                query_rep = f"""
                    SELECT id, reputation_score
                    FROM agents
                    WHERE id IN ({placeholders_missing}) AND tenant_id = ?
                """
                params_rep = missing_candidates + [tenant_id]
                async with conn.execute(query_rep, params_rep) as cursor:
                    rows_rep = await cursor.fetchall()
                    for id_rep, rep in rows_rep:
                        # Normalize overall reputation to an eroi-equivalent range
                        eroi_map[id_rep] = rep * 0.9
            
            # For any agent that still has no entry anywhere, default to 0.45
            for cid in candidate_agent_ids:
                if cid not in eroi_map:
                    eroi_map[cid] = 0.45
                    
            # Return candidate with maximum score
            return max(candidate_agent_ids, key=lambda cid: eroi_map[cid])
