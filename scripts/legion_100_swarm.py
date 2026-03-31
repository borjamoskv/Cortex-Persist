#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
LEGION SWARM 100: The Sovereign Century Audit.
Orchestrates 100 specialized agents across 3 functional squadrons:
P0: Integrity (30), P1: Kinetic (40), P2: Ghost Hunt (30).
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# ── SOVEREIGN PATH ANCHOR ──
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cortex.engine import CortexEngine
from cortex.engine.squadrons import GhostHuntSquadron, IntegritySquadron, KineticSquadron

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legion_100")

def render_grid(signals: list[Any]):
    """Renders a 10x10 visual grid of the 100 agents."""
    print("\n" + "═"*41)
    print(" ⚜  LEGION SWARM 100: VISUAL STATUS GRID ⚜")
    print("═"*41)
    
    # Sort signals by agent name to ensure deterministic grid position
    sorted_signals = sorted(signals, key=lambda x: x.agent_id)
    
    for i in range(0, 100):
        if i < len(sorted_signals):
            sig = sorted_signals[i]
            if sig.status == "SUCCESS":
                char = "💎" # Result found
            elif sig.status == "VOID":
                char = "⚫" # No findings
            elif sig.status == "FAILURE":
                char = "💀" # Crash
            else:
                char = "⚪"
        else:
            char = "◌"
            
        print(char, end=" " if (i + 1) % 10 != 0 else "\n")
    print("═"*41 + "\n")

async def main():
    engine = CortexEngine(":memory:", auto_embed=False)
    await engine.init_db()
    
    # Target: The entire workspace or a specific directory
    target_root = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # 1. Instantiate Squadrons
    p0 = IntegritySquadron(engine)
    p1 = KineticSquadron(engine)
    p2 = GhostHuntSquadron(engine)
    
    print(f"🚀 Launching Legion Swarm 100 against: {target_root}")
    
    # 2. Deploy concurrently
    # Note: Each squadron handles its own replicas (30+40+30=100)
    await asyncio.gather(
        p0.deploy(target_root),
        p1.deploy(target_root),
        p2.deploy(target_root)
    )
    
    # 3. Aggregate all signals for the grid
    all_signals = []
    all_signals.extend(await p0.bus.get_all())
    all_signals.extend(await p1.bus.get_all())
    all_signals.extend(await p2.bus.get_all())
    
    # 4. Render Final Dashboard
    render_grid(all_signals)
    
    # 5. Summary Report
    success = sum(1 for s in all_signals if s.status == "SUCCESS")
    voids = sum(1 for s in all_signals if s.status == "VOID")
    failures = sum(1 for s in all_signals if s.status == "FAILURE")
    
    print("📊 FINAL CRYSTALLIZATION:")
    print(f"   - Total Agents: {len(all_signals)}")
    print(f"   - Success/Findings: {success}")
    print(f"   - Void/Clean: {voids}")
    print(f"   - Failures: {failures}")
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
