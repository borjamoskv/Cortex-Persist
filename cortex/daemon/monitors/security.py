"""Security monitor for MOSKV daemon."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortex import config
from cortex.daemon.models import SecurityAlert
from cortex.database.core import connect_async
from cortex.memory.encoder import AsyncEncoder

try:
    from cortex.memory.vector_store import VectorStoreL2
except ImportError:
    VectorStoreL2 = None  # type: ignore[assignment,misc]

logger = logging.getLogger("moskv-daemon")


class SecurityMonitor:
    """Runs security threat intel pipeline against API/Firewall logs.

    Ingests recent anomaly logs, vectorizes them (L2 semantic space),
    and checks for high-similarity against known fraud/attack patterns.
    """

    def __init__(self, log_path: str = "~/.cortex/firewall.log", threshold: float = 0.85):
        self.log_path = Path(log_path).expanduser()
        self.threshold = threshold
        self._encoder: AsyncEncoder | None = None
        self._vector_store: VectorStoreL2 | None = None

    async def _get_store(self) -> VectorStoreL2:
        """Lazily initialize the local LLM encoder and L2 vector store."""
        if self._vector_store and self._encoder:
            return self._vector_store

        self._encoder = AsyncEncoder()
        # Initialize the encoder so it downloads model if needed
        await self._encoder.initialize()

        self._vector_store = VectorStoreL2(encoder=self._encoder, db_path="~/.cortex/vectors")
        await self._vector_store.ensure_collection()
        return self._vector_store

    def _read_recent_events(self) -> list[dict[str, Any]]:
        """Reads the tail of the firewall/API log for unprocessed events."""
        events = []
        if not self.log_path.exists():
            # Seed a dummy log or return empty if absent
            return events

        try:
            # Simple simulation: read all lines, assuming it's manageable
            # In a sovereign KETER-level system we would track read offsets
            # Lee el log entero y lo vacía para que no se re-analicen los mismos eventos.
            lines = self.log_path.read_text().splitlines()
            self.log_path.write_text("")

            for line in lines[-500:]:  # process at most the last 500 events
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError as e:
            logger.error("Failed to read/clear security logs: %s", e)
        return events

    async def check_async(self) -> list[SecurityAlert]:
        """Vectorizes recent events and searches for semantic attack similarities."""
        alerts: list[SecurityAlert] = []
        events = self._read_recent_events()

        if not events:
            return alerts

        try:
            store = await self._get_store()
            for event in events:
                alert = await self._process_single_event(store, event)
                if alert:
                    alerts.append(alert)

            if alerts:
                c5_alerts = [a for a in alerts if a.confidence == "C5"]
                if c5_alerts:
                    await self._blacklist_ips(c5_alerts)
        except Exception as e:
            logger.error("SecurityMonitor check_async failed: %s", e)
        return alerts

    async def _process_single_event(
        self, store: VectorStoreL2, event: dict[str, Any]
    ) -> SecurityAlert | None:
        """Process a single event and return an alert if a threat is detected."""
        payload = event.get("payload", "")
        if not payload:
            return None

        # Query L2 vector store for structurally/semantically similar attacks
        results = await store.recall(query=payload, limit=1, score_threshold=self.threshold)
        if not results:
            return None

        top_match = results[0]
        similarity = top_match["score"]
        summary = top_match.get("content", "Unknown historical attack pattern")
        confidence = "C5" if similarity > 0.92 else "C4"

        return SecurityAlert(
            ip_address=event.get("ip_address", "0.0.0.0"),
            payload=payload[:100] + "..." if len(payload) > 100 else payload,
            similarity_score=similarity,
            confidence=confidence,
            summary=f"Matches known vector: {summary[:50]}",
            timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )

    async def _blacklist_ips(self, alerts: list[SecurityAlert]) -> None:
        """Persist C5 alerts to the threat_intel blacklist."""
        db_path = config.DB_PATH
        try:
            async with await connect_async(db_path) as conn:
                for alert in alerts:
                    await self._save_threat(conn, alert)
                await conn.commit()
                logger.error("🔥 KILL SWITCH: Blacklisted %d IPs.", len(alerts))
        except Exception:
            logger.error("Failed to save threat intel to DB")

    async def _save_threat(self, conn: Any, alert: SecurityAlert) -> None:
        """Save a single threat to the DB."""
        try:
            await conn.execute(
                "INSERT INTO threat_intel (ip_address, reason, confidence) VALUES (?, ?, ?)",
                (alert.ip_address, alert.summary, alert.confidence),
            )
        except sqlite3.IntegrityError:
            pass

    def check(self) -> list[SecurityAlert]:
        """Synchronous wrapper for check_async."""
        try:
            return asyncio.run(self.check_async())
        except RuntimeError as e:
            if "running event loop" not in str(e):
                raise
            if not hasattr(self, "_bg_tasks"):
                self._bg_tasks: set = set()

            task = asyncio.ensure_future(self.check_async())
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
            return []
