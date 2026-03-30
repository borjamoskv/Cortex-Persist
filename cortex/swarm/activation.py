"""
cortex/swarm/activation.py
─────────────────────────
Sovereign Swarm Activation Logic

Final validation and ignition of the Ouroboros-Ω swarm.
"""

import asyncio
import logging
from .ouroboros_omega import OuroborosOmega
from .discovery_omega import DiscoveryOmega

logger = logging.getLogger("cortex.swarm.activation")

async def activate_swarm(target_exergy: float = 1000.0):
    """
    Ignites the swarm engine.
    """
    logger.info(" [ACTIVATION] Starting Sovereign Swarm Activation...")
    discovery = DiscoveryOmega()
    swarm = OuroborosOmega(discovery=discovery)
    
    # 1. Warm up prefix caches (KV-Aware)
    # 2. Synchronize Specialist status
    # 3. Enter extraction loop
    
    logger.info(" [ACTIVATION] Swarm online. Ouroboros-Ω enabled.")
    return swarm

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(activate_swarm())
