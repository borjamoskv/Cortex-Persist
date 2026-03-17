"""
Sovereign Reporter — The Living Documentation Engine (Ω-Dynamic).

NOOSPHERE-Ω: The Self-Aware Chronicler.
This engine extracts real-time metadata from the CORTEX database
and generates dynamic documentation artifacts (JSON/HTML).
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger("cortex.reporter")


@dataclass
class ManifoldStatus:
    timestamp: str
    project: str
    causality: dict[str, Any]
    efficiency: dict[str, Any]
    signals: dict[str, Any]
    architecture_integrity: float
    active_ghosts: int
    db_size_mb: float
    total_facts: int


class SovereignReporter:
    """Generates dynamic documentation from the live CORTEX state."""

    def __init__(self, db_path: str, project: str = "system"):
        self.db_path = db_path
        self.project = project

    async def _fetch_roi_history(self, conn: aiosqlite.Connection) -> list[dict[str, Any]]:
        """Fetch the latest ROI records from the facts table."""
        cursor = await conn.execute(
            "SELECT content, metadata FROM facts WHERE fact_type='knowledge' "
            "AND source='chronos-roi' ORDER BY id DESC LIMIT 5"
        )
        roi_history = []
        rows = await cursor.fetchall()
        for row in rows:
            try:
                roi_history.append(json.loads(row[1]))
            except (json.JSONDecodeError, TypeError):
                continue
        return roi_history

    async def collect_metrics(self) -> ManifoldStatus:
        """Aggregate data from all Ω-dimensions using Async I/O."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 130/100: Reusing existing CausalGraph/SignalBus (assuming they
                # can be adapted or we query directly for speed)
                # Since CausalGraph and SignalBus take a sync sqlite3.Connection
                # in this architecture context, we will perform raw fast async
                # queries for the stats here to achieve 0-gravity I/O.

                # 1. Causality Stats
                cursor = await conn.execute("SELECT COUNT(*) FROM causal_edges")
                row = await cursor.fetchone()
                total_edges = row[0] if row else 0
                causal_stats = {"total_edges": total_edges}

                # 2. Signals Stats
                cursor = await conn.execute("SELECT COUNT(*) FROM signals")
                row = await cursor.fetchone()
                total_signals = row[0] if row else 0

                # Anomaly specific signal detection
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM signals WHERE event_type='sap_anomaly'"
                )
                row = await cursor.fetchone()
                anomaly_count = row[0] if row else 0

                signal_stats = {"total": total_signals, "sap_anomaly": bool(anomaly_count > 0)}

                # 3. Efficiency (ROI)
                roi_history = await self._fetch_roi_history(conn)

                # 4. Active Ghosts
                cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE fact_type='ghost'")
                row = await cursor.fetchone()
                ghost_count = row[0] if row else 0

                # 5. Architecture Integrity
                cursor = await conn.execute("SELECT COUNT(*) FROM facts")
                row = await cursor.fetchone()
                fact_count = row[0] if row else 0
                integrity = (total_edges / max(1, fact_count)) * 100.0

                db_size_mb = 0.0
                if os.path.exists(self.db_path):
                    db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)

                return ManifoldStatus(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    project=self.project,
                    causality=causal_stats,
                    efficiency={
                        "latest_roi": roi_history[0] if roi_history else {},
                        "history_count": len(roi_history),
                    },
                    signals=signal_stats,
                    architecture_integrity=round(min(100.0, integrity), 2),
                    active_ghosts=ghost_count,
                    db_size_mb=db_size_mb,
                    total_facts=fact_count,
                )
        except (sqlite3.Error, OSError) as e:
            logger.error("Failed to collect metrics: %s", e)
            raise

    async def stream_metrics(self, interval: float = 0.05):
        """Yield metrics continuously, leveraging PRAGMA data_version to only yield on change."""
        last_version = None
        # Send initial state
        try:
            yield await self.collect_metrics()
        except sqlite3.Error:
            pass

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("PRAGMA data_version")
                row = await cursor.fetchone()
                last_version = row[0] if row else 0

                while True:
                    await asyncio.sleep(interval)
                    cursor = await conn.execute("PRAGMA data_version")
                    row = await cursor.fetchone()
                    current_version = row[0] if row else 0

                    if current_version != last_version:
                        last_version = current_version
                        yield await self.collect_metrics()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — stream boundary must not crash system
            logger.error("Error in stream_metrics: %s", e)

    async def export_json(self, output_path: str):
        """Export status to a JSON file for frontend consumption."""
        status = await self.collect_metrics()
        data = asdict(status)

        def _write() -> None:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        await asyncio.to_thread(_write)
        logger.info("Dynamic documentation exported to %s", output_path)

    async def generate_markdown_report(self) -> str:
        """Generates a markdown snippet for OMEGA_MANIFOLD.md integration."""
        s = await self.collect_metrics()
        return f"""
### 📊 Live Manifold Telemetry ({s.timestamp})
- **Architecture Integrity:** {s.architecture_integrity}%
- **Causal Traceability:** {s.causality["total_edges"]} edges mapped
- **Signal Density:** {s.signals["total"]} persistent signals
- **Efficiency (ROI):** {s.efficiency["latest_roi"].get("roi_ratio", 0)}x current boost
- **Active Ghosts:** {s.active_ghosts} pending resolutions
"""


if __name__ == "__main__":
    db = os.path.expanduser("~/.cortex/cortex.db")
    if not os.path.exists(db):
        sys.stderr.write(f"Error: Database not found at {db}\n")
        sys.exit(1)

    reporter = SovereignReporter(db)
    # Export for web dashboard
    asyncio.run(reporter.export_json("docs/data/manifold_status.json"))
    # Print for console integration
    report = asyncio.run(reporter.generate_markdown_report())
    sys.stdout.write(report)
