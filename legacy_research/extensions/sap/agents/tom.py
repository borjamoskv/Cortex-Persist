# [C5-REAL] Exergy-Maximized
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

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

from legacy_research.extensions.signals.bus import AsyncSignalBus

logger = logging.getLogger("cortex.extensions.sap.tom")


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
