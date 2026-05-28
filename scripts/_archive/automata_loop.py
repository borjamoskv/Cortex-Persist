#!/usr/bin/env python3
"""∴ CORTEX-AUTOMATA-LOOP v0.1 — Sovereign Actuator.

Orchestrates the auxiliary swarm by processing triaged targets from the ledger.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Fix PYTHONPATH to include project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

try:
    from scripts.db import get_bounties, update_bounty_status
    from scripts.agent_hound_omega import build_mythos_graph
    from scripts.exergy_governor import ExergyGovernor
except ImportError:
    print("[!] CORTEX-TERMINAL: Dependency failure. Check PYTHONPATH.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CORTEX.AUTOMATA")

# Initialize Sovereign Governor
governor = ExergyGovernor()

async def process_target(engine, bounty):
    """Processes a single bounty through the Hound-Omega engine."""
    logger.info(f"◈ [STRIKE] Initiating analysis for: {bounty['title']}")
    
    # Phase 0: Exergy Routing
    target_code = bounty.get("contract_snippet", "// Code pending acquisition...")
    route_info = governor.route(target_code, requested_model="gemini-1.5-pro")
    
    if route_info["routing_reason"] != "REQUESTED_BY_OPERATOR":
        logger.info(f"◈ [EXERGY_ROUTED] {route_info['routing_reason']} -> Using {route_info['model']}")

    # Initialize the LangGraph state
    initial_state = {
        "messages": [],
        "bounty_url": bounty["url"],
        "target_code": target_code,
        "hypotheses": [],
        "scaffold_commands": [],
        "proof_of_concept": "",
        "is_verified": False,
        "iterations": 0,
        "metadata": {
            "routed_model": route_info["model"],
            "pci": route_info["pci"]
        }
    }
    
    try:
        # Run the Mythos Graph (Hound-Omega)
        import time
        start_time = time.time()
        final_state = await engine.ainvoke(initial_state)
        duration = (time.time() - start_time) * 1000
        
        # Phase 4: Record Exergy Outcome
        # In a real scenario, we'd extract actual token counts from the LLM response object.
        # Here we verify_native based on length for the prototype's learning loop.
        actual_tokens = len(str(final_state)) // 4 
        governor.log_result(target_code, route_info, actual_tokens, duration)
        
        if final_state.get("is_verified"):
            logger.info(f"✨ [CERTIFIED] Bounty verified: {bounty['title']}")
            update_bounty_status(bounty["id"], "audited")
        else:
            logger.warning(f"○ [ARCHIVED] Could not certify: {bounty['title']}")
            update_bounty_status(bounty["id"], "unverifiable")
            
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Actuation failure for {bounty['id']}: {e}")

async def main_loop():
    """Continuous extraction loop."""
    logger.info("∴ CORTEX-AUTOMATA-LOOP STARTING [Ω-PROTOCOLS ACTIVE]")
    
    # Compile the Hound-Omega graph once
    engine = build_mythos_graph()
    
    while True:
        # 1. Fetch triaged targets
        targets = get_bounties(status="found", min_exergy=1.5, limit=5)
        
        if not targets:
            logger.info("○ [IDLE] No qualifying targets in ledger. Sleeping 60s.")
            await asyncio.sleep(60)
            continue
            
        logger.info(f"◈ [QUEUE] {len(targets)} targets queued for actuation.")
        
        # 2. Process targets sequentially to conserve API and thermal budget
        for target in targets:
            await process_target(engine, target)
            # Subtle delay to prevent rate limiting
            await asyncio.sleep(2)
            
        logger.info("◈ [CYCLE_COMPLETE] Cooling down...")
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("∴ [HALT] Automata loop terminated by operator.")
