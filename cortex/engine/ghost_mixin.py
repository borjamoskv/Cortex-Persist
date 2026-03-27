"""
Ghost Field Mixin (v5.4) — Cognitive Hypervisor Activation.

Operational logic for registering and resolving 'ghost' states (latent intents).
This mixin provides the mechanism to track work-in-progress or speculative
states that are not yet committed as verified facts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from cortex.engine.mixins.base import EngineMixinBase

logger = logging.getLogger("cortex.ghost")


class GhostMixin(EngineMixinBase):
    """Cognitive Hypervisor: Interface for the Ghost Field."""

    async def register_ghost(
        self,
        reference: str,
        project: str,
        context: str = "",
        tenant_id: str = "default",
        meta: dict | None = None,
    ) -> int:
        """Register a new ghost intent in the ledger.

        This signals the 'birth' of a speculative state in the hypervisor.
        """
        meta_json = json.dumps(meta or {})
        sql = """
            INSERT INTO ghosts (tenant_id, reference, context, project, status, meta)
            VALUES (?, ?, ?, ?, 'open', ?)
        """
        params = (tenant_id, reference, context, project, meta_json)

        # Execute write via engine session
        async with self.session() as conn:  # type: ignore
            cursor = await conn.execute(sql, params)
            ghost_id = cursor.lastrowid
            await conn.commit()

        # Ω₁₃: Ledger Audit Trail
        if hasattr(self, "ledger") and self.ledger:  # type: ignore
            await self.ledger.record_transaction(  # type: ignore
                project=project,
                action="GHOST_BIRTH",
                detail={"reference": reference, "ghost_id": ghost_id},
                tenant_id=tenant_id,
            )

        logger.info("GHOST_BIRTH: %s (id=%s) in %s", reference, ghost_id, project)
        return ghost_id  # type: ignore

    async def resolve_ghost(
        self,
        ghost_id: int,
        target_id: int,
        confidence: float = 1.0,
    ) -> bool:
        """Resolve a ghost intent into a verified fact (target_id)."""
        now = datetime.now().isoformat()
        sql = """
            UPDATE ghosts
            SET status = 'resolved',
                target_id = ?,
                resolved_at = ?,
                confidence = ?
            WHERE id = ?
        """
        params = (target_id, now, confidence, ghost_id)

        async with self.session() as conn:  # type: ignore
            async with conn.execute(
                "SELECT project, reference, tenant_id FROM ghosts WHERE id = ?", (ghost_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    logger.warning("GHOST_RESOLVE_FAIL: Ghost %s not found", ghost_id)
                    return False
                project, reference, tenant_id = row

            await conn.execute(sql, params)
            await conn.commit()

        # Ω₁₃: Ledger Audit Trail
        if hasattr(self, "ledger") and self.ledger:  # type: ignore
            await self.ledger.record_transaction(  # type: ignore
                project=project,
                action="GHOST_RESOLVE",
                detail={
                    "reference": reference,
                    "target_id": target_id,
                    "confidence": confidence,
                    "ghost_id": ghost_id,
                },
                tenant_id=tenant_id,
            )

        logger.info("GHOST_RESOLVE: %s (id=%s) -> Fact %s", reference, ghost_id, target_id)
        return True

    async def list_active_ghosts(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """List all open ghost intents."""
        sql = "SELECT * FROM ghosts WHERE status = 'open' AND tenant_id = ?"
        params: list[Any] = [tenant_id]

        if project:
            sql += " AND project = ?"
            params.append(project)

        async with self.session() as conn:  # type: ignore
            async with conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                # Simple row to dict conversion
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row, strict=True)) for row in rows]
