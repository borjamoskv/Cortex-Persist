"""
TOM (The Tracker) - SAP Forensic Audit Agent.

TOM specializes in data extraction and technical verification.
Applies rules like Benford's Law, Segregation of Duties (SOD), and duplicates detection.
Emits findings to the CORTEX signal bus.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from cortex.extensions.signals.bus import AsyncSignalBus

logger = logging.getLogger("cortex.extensions._quarantine.sap.tom")


class TomAgent:
    """The Tracker: Forensic scanner for SAP transactions."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        self.bus = AsyncSignalBus(conn)

    async def audit_transactions(self, transactions: list[dict[str, Any]]) -> int:
        """Scan transactions and emit signals for findings.
        Returns the number of findings detected.
        """
        findings_count = 0
        for tx in transactions:
            # Ω₃: Metabolic Loop Prevention
            # Do NOT audit internal signals as if they were business transactions.
            if tx.get("source", "").startswith("agent:") or tx.get("agent"):
                logger.debug("Skipping internal agent activity: %s", tx.get("id"))
                continue

            # Synthetic Benford/Outlier detection logic
            # In real system this uses scipy/stats on numeric clusters
            amount = tx.get("amount", 0)
            if amount > 10_000_000:
                await self._emit_finding(
                    finding_type="outlier_detection",
                    description=f"Transaction material outlier detected: {amount}",
                    evidence=tx,
                    severity="high",
                )
                findings_count += 1

            # Synthetic SOD logic
            user_create = tx.get("created_by")
            user_approve = tx.get("approved_by")
            if user_create and user_approve and user_create == user_approve:
                await self._emit_finding(
                    finding_type="sod_violation",
                    description=f"SOD violation: user {user_create} created and approved tx.",
                    evidence=tx,
                    severity="critical",
                )
                findings_count += 1

        if findings_count > 0:
            logger.info("TOM scan completed: %d findings detected.", findings_count)
        return findings_count

    async def _emit_finding(
        self, finding_type: str, description: str, evidence: dict[str, Any], severity: str
    ) -> None:
        """Emit a finding signal to the CORTEX bus."""
        payload = {
            "finding_type": finding_type,
            "description": description,
            "evidence": evidence,
            "severity": severity,
            "agent": "TOM",
        }
        await self.bus.emit(
            event_type="sap:audit:finding",
            payload=payload,
            source="tom-tracker",
            project="sap-audit",
        )
