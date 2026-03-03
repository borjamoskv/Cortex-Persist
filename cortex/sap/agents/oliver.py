"""
OLIVER (The Hammer) - SAP Effect Execution Agent.

OLIVER specializes in materiality evaluation and strategic effect application.
Listens to TOM's findings via the signal bus and translates technical anomalies
into systemic effects (blocks, freeze, notifications).
"""

from __future__ import annotations

import logging

import aiosqlite

from cortex.signals.bus import AsyncSignalBus

logger = logging.getLogger("cortex.sap.oliver")


class OliverAgent:
    """The Hammer: Materiality evaluator and executioner."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        self.bus = AsyncSignalBus(conn)

    async def listen_and_react(self, limit: int = 50) -> int:
        """Poll signals emitted by TOM and convert to material effects.
        Returns the number of effects emitted.
        """
        # Consume unread finding signals from TOM
        signals = await self.bus.poll(
            event_type="sap:audit:finding",
            source="tom-tracker",
            project="sap-audit",
            consumer="oliver-hammer",
            limit=limit,
        )

        effects_count = 0
        for sig in signals:
            payload = sig.payload
            severity = payload.get("severity", "low")
            finding_type = payload.get("finding_type", "unknown")
            evidence = payload.get("evidence", {})

            # Materiality evaluation matrix
            materiality_score = self._evaluate_materiality(severity, evidence)

            action = "LOG_ONLY"
            if materiality_score >= 0.80:
                action = "BLOCK_USER"
            elif materiality_score >= 0.60:
                action = "FREEZE_ACCOUNT"
            elif materiality_score >= 0.30:
                action = "NOTIFY_BOARD"

            if action != "LOG_ONLY":
                await self._emit_effect(
                    action=action,
                    materiality=materiality_score,
                    trigger_finding=payload,
                )
                effects_count += 1
                logger.warning(
                    "OLIVER Action [%s] Materiality: %.2f on finding: %s",
                    action,
                    materiality_score,
                    finding_type,
                )

        return effects_count

    def _evaluate_materiality(self, severity: str, evidence: dict) -> float:
        """Calculate materiality score (0.0 to 1.0) based on severity and amounts."""
        score = 0.0
        if severity == "critical":
            score += 0.5
        elif severity == "high":
            score += 0.3

        amount = evidence.get("amount", 0)
        # Assuming >= €10M is extremely material
        if amount >= 10_000_000:
            score += 0.4
        elif amount >= 1_000_000:
            score += 0.2

        return min(1.0, score)

    async def _emit_effect(self, action: str, materiality: float, trigger_finding: dict) -> None:
        """Emit an effect signal back to the bus for system-wide execution."""
        payload = {
            "action": action,
            "materiality": materiality,
            "trigger_finding": trigger_finding,
            "agent": "OLIVER",
        }
        await self.bus.emit(
            event_type="sap:audit:effect",
            payload=payload,
            source="oliver-hammer",
            project="sap-audit",
        )
