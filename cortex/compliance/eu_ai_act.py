# [C5-REAL] Exergy-Maximized
"""
EU AI Act Compliance Engine.

Automates the generation of regulatory artifacts, AI Decision Reports (Article 13),
and Human Oversight escalation gating (Article 14).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from cortex.database.core import connect_async, connect_async_ctx


logger = logging.getLogger("cortex.compliance.eu_ai_act")


class AIDecisionReport:
    """Generates an Article 13 Transparency Report for a specific decision."""

    @staticmethod
    def generate(
        audit_id: str,
        tenant_id: str,
        actor_id: str,
        action: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        confidence_score: float,
        evidence_score: float,
    ) -> dict[str, Any]:
        """
        Generates a transparent, human-readable record of an autonomous decision.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        report = {
            "report_version": "1.0",
            "compliance_framework": "EU_AI_ACT_ART_13",
            "timestamp": timestamp,
            "audit_id": audit_id,
            "tenant_id": tenant_id,
            "decision_context": {
                "actor": actor_id,
                "action_type": action,
            },
            "parameters": {
                "inputs_hashed": hashlib.sha256(
                    json.dumps(input_data, sort_keys=True).encode()
                ).hexdigest(),
                "outputs_hashed": hashlib.sha256(
                    json.dumps(output_data, sort_keys=True).encode()
                ).hexdigest(),
            },
            "robustness_metrics": {
                "confidence_score": confidence_score,
                "evidence_score": evidence_score,
            },
            "human_oversight_required": confidence_score < 0.85 or evidence_score < 0.70,
        }
        return report


class HumanOversightGate:
    """Manages Article 14 Human Oversight (Escalation / Approve / Reject)."""

    def __init__(self, db_path: str = "cortex_compliance.db"):
        self.db_path = db_path

    async def _init_db(self, conn: aiosqlite.Connection) -> None:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS oversight_gates (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                status TEXT NOT NULL,
                reviewer_id TEXT,
                review_timestamp TEXT,
                comments TEXT
            )
        """)
        await conn.commit()

    async def escalate(self, audit_id: str, tenant_id: str, reason: str) -> None:
        """Escalates a decision for human review."""
        async with connect_async_ctx(self.db_path) as conn:
            await self._init_db(conn)
            await conn.execute(
                "INSERT OR REPLACE INTO oversight_gates (audit_id, tenant_id, status, comments) VALUES (?, ?, ?, ?)",
                (audit_id, tenant_id, "PENDING_REVIEW", reason),
            )
            await conn.commit()
        logger.warning(f"[HumanOversight] Decision {audit_id} escalated for human review: {reason}")

    async def approve(self, audit_id: str, reviewer_id: str, comments: str = "") -> None:
        """Approves an escalated decision."""
        timestamp = datetime.now(timezone.utc).isoformat()
        async with connect_async_ctx(self.db_path) as conn:
            await self._init_db(conn)
            await conn.execute(
                "UPDATE oversight_gates SET status = ?, reviewer_id = ?, review_timestamp = ?, comments = ? WHERE audit_id = ?",
                ("APPROVED", reviewer_id, timestamp, comments, audit_id),
            )
            await conn.commit()
        logger.info(f"[HumanOversight] Decision {audit_id} APPROVED by {reviewer_id}.")

    async def reject(self, audit_id: str, reviewer_id: str, comments: str = "") -> None:
        """Rejects an escalated decision."""
        timestamp = datetime.now(timezone.utc).isoformat()
        async with connect_async_ctx(self.db_path) as conn:
            await self._init_db(conn)
            await conn.execute(
                "UPDATE oversight_gates SET status = ?, reviewer_id = ?, review_timestamp = ?, comments = ? WHERE audit_id = ?",
                ("REJECTED", reviewer_id, timestamp, comments, audit_id),
            )
            await conn.commit()
        logger.info(f"[HumanOversight] Decision {audit_id} REJECTED by {reviewer_id}.")

    async def get_status(self, audit_id: str) -> str | None:
        """Gets the status of an escalated decision."""
        async with connect_async_ctx(self.db_path) as conn:
            await self._init_db(conn)
            cursor = await conn.execute(
                "SELECT status FROM oversight_gates WHERE audit_id = ?", (audit_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
