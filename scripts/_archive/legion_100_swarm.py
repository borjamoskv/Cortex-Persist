#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
LEGION SWARM 100: The Sovereign Century Audit.
Orchestrates 100 specialized agents across 3 functional squadrons:
P0: Silver/Gold (40), P1: Lead/Void (40), P2: Sovereign (20).
Integrates Nemesis L4 (10%).
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
from cortex.engine.squadrons import (
    GoldPhalanx,
    LeadPhalanx,
    SilverPhalanx,
    SovereignPhalanx,
    VoidPhalanx,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("legion_100")


def render_grid(signals: list[Any]):
    """Renders a 10x10 visual grid of the 100 agents."""
    print("\n" + "═" * 41)
    print(" ⚜  LEGION SWARM 100: VISUAL STATUS GRID ⚜")
    print("═" * 41)

    # Sort signals by agent name to ensure deterministic grid position
    sorted_signals = sorted(signals, key=lambda x: x.agent_id)

    for i in range(0, 100):
        if i < len(sorted_signals):
            sig = sorted_signals[i]
            if sig.status == "SUCCESS":
                char = "💎"  # Result found
            elif sig.status == "VOID":
                char = "⚫"  # No findings
            elif sig.status == "FAILURE":
                char = "💀"  # Crash
            else:
                char = "⚪"
        else:
            char = "◌"

        print(char, end=" " if (i + 1) % 10 != 0 else "\n")
    print("═" * 41 + "\n")


async def main():
    engine = CortexEngine(":memory:", auto_embed=False)
    await engine.init_db()

    # Target: The entire workspace or a specific directory
    target_root = sys.argv[1] if len(sys.argv) > 1 else "."

    # 1. Instantiate Phalanxes (5 Phalanxes * 20 Agents = 100 Agents)
    # The Sovereign Phalanx will contain the Omega-class agents, the others will contain L4s.
    p_silver = SilverPhalanx(engine)
    p_gold = GoldPhalanx(engine)
    p_lead = LeadPhalanx(engine)
    p_void = VoidPhalanx(engine)
    p_sovereign = SovereignPhalanx(engine)

    print(f"🚀 Launching Legion Swarm 100 against: {target_root}")

    # 2. Deploy in parallel (100-Agent Burst Approach)
    print("\n--- 🌟 Dispatching 100-Agent Parallel Burst (Silver, Gold, Lead, Void, Sovereign) ---")
    await asyncio.gather(
        p_silver.deploy(target_root),
        p_gold.deploy(target_root),
        p_lead.deploy(target_root),
        p_void.deploy(target_root),
        p_sovereign.deploy(target_root),
    )

    # 3. Aggregate all signals for the grid
    all_signals = []
    all_signals.extend(await p_silver.bus.get_all())
    all_signals.extend(await p_gold.bus.get_all())
    all_signals.extend(await p_lead.bus.get_all())
    all_signals.extend(await p_void.bus.get_all())
    all_signals.extend(await p_sovereign.bus.get_all())

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

    if success > 0:
        print("\n🔍 DETAILED FINDINGS:")
        for s in all_signals:
            if s.status == "SUCCESS":
                for finding in s.payload.get("findings", []):
                    print(f"   [!] {s.agent_id} on {s.target}: {finding}")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
