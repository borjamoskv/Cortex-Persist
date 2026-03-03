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

from cortex.engine.causality import CausalGraph
from cortex.signals.bus import SignalBus

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

    def _fetch_roi_history(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        """Fetch the latest ROI records from the facts table."""
        cursor = conn.execute(
            "SELECT content, meta FROM facts WHERE fact_type='knowledge' "
            "AND source='chronos-roi' ORDER BY created_at DESC LIMIT 5"
        )
        roi_history = []
        for row in cursor.fetchall():
            try:
                roi_history.append(json.loads(row[1]))
            except (json.JSONDecodeError, TypeError):
                continue
        return roi_history

    def collect_metrics(self) -> ManifoldStatus:
        """Aggregate data from all Ω-dimensions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                graph = CausalGraph(conn)
                bus = SignalBus(conn)
                
                # 1. Causality Stats
                causal_stats = graph.stats()
                
                # 2. Signals Stats
                signal_stats = bus.stats()
                
                # 3. Efficiency (ROI)
                roi_history = self._fetch_roi_history(conn)
                
                # 4. Active Ghosts (TODOs in code + DB ghosts)
                # For now, we query the facts table for 'ghost' types
                cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE fact_type='ghost'")
                ghost_count = cursor.fetchone()[0]

                # 5. Architecture Integrity (Calculated heuristic)
                # Coverage of facts by causal edges
                fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
                edge_count = causal_stats.get("total_edges", 0)
                integrity = (edge_count / max(1, fact_count)) * 100.0

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

    def export_json(self, output_path: str):
        """Export status to a JSON file for frontend consumption."""
        status = self.collect_metrics()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(asdict(status), f, indent=2)
        logger.info("Dynamic documentation exported to %s", output_path)

    def generate_markdown_report(self) -> str:
        """Generates a markdown snippet for OMEGA_MANIFOLD.md integration."""
        s = self.collect_metrics()
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
