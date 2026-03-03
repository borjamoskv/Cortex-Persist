"""
Sovereign Reporter — The Living Documentation Engine (Ω-Dynamic).

NOOSPHERE-Ω: The Self-Aware Chronicler.
This engine extracts real-time metadata from the CORTEX database
and generates dynamic documentation artifacts (JSON/HTML).
"""

import json
import logging
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
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

class SovereignReporter:
    """Generates dynamic documentation from the live CORTEX state."""

    def __init__(self, db_path: str, project: str = "system"):
        self.db_path = db_path
        self.project = project

    async def _fetch_roi_history(self, conn: aiosqlite.Connection) -> list[dict[str, Any]]:
        """Fetch the latest ROI records from the facts table."""
        cursor = await conn.execute(
            "SELECT content, meta FROM facts WHERE fact_type='knowledge' "
            "AND source='chronos-roi' ORDER BY created_at DESC LIMIT 5"
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
                total_edges = (await cursor.fetchone())[0]
                causal_stats = {"total_edges": total_edges}
                
                # 2. Signals Stats
                cursor = await conn.execute("SELECT COUNT(*) FROM signals")
                total_signals = (await cursor.fetchone())[0]
                signal_stats = {"total": total_signals}
                
                # 3. Efficiency (ROI)
                roi_history = await self._fetch_roi_history(conn)
                
                # 4. Active Ghosts
                cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE fact_type='ghost'")
                ghost_count = (await cursor.fetchone())[0]

                # 5. Architecture Integrity
                cursor = await conn.execute("SELECT COUNT(*) FROM facts")
                fact_count = (await cursor.fetchone())[0]
                integrity = (total_edges / max(1, fact_count)) * 100.0

                return ManifoldStatus(
                    timestamp=datetime.now().isoformat(),
                    project=self.project,
                    causality=causal_stats,
                    efficiency={
                        "latest_roi": roi_history[0] if roi_history else {},
                        "history_count": len(roi_history)
                    },
                    signals=signal_stats,
                    architecture_integrity=round(min(100.0, integrity), 2),
                    active_ghosts=ghost_count
                )
        except (sqlite3.Error, OSError) as e:
            logger.error("Failed to collect metrics: %s", e)
            raise

    async def export_json(self, output_path: str):
        """Export status to a JSON file for frontend consumption."""
        status = await self.collect_metrics()
        # Rest of export code...
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(asdict(status), f, indent=2)
        logger.info("Dynamic documentation exported to %s", output_path)

    async def generate_markdown_report(self) -> str:
        """Generates a markdown snippet for OMEGA_MANIFOLD.md integration."""
        s = await self.collect_metrics()
        return f"""
### 📊 Live Manifold Telemetry ({s.timestamp})
- **Architecture Integrity:** {s.architecture_integrity}%
- **Causal Traceability:** {s.causality['total_edges']} edges mapped
- **Signal Density:** {s.signals['total']} persistent signals
- **Efficiency (ROI):** {s.efficiency['latest_roi'].get('roi_ratio', 0)}x current boost
- **Active Ghosts:** {s.active_ghosts} pending resolutions
"""

if __name__ == "__main__":
    db = os.path.expanduser("~/.cortex/cortex.db")
    if not os.path.exists(db):
        print(f"Error: Database not found at {db}")
        sys.exit(1)
        
    reporter = SovereignReporter(db)
    # Export for web dashboard
    reporter.export_json("docs/data/manifold_status.json")
    # Print for console integration
    print(reporter.generate_markdown_report())
