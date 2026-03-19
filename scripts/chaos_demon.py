"""
CHAOS DEMON — The Nemesis of CORTEX.

Orchestrates the "Attack -> Fail -> Forge -> Verify" loop.
"""

import asyncio
import logging

from cortex.extensions.immune.antibody_forge import AntibodyForge
from cortex.extensions.immune.chaos import ChaosGate, ChaosScenario, async_interceptor
from cortex.extensions.immune.error_boundary import ErrorBoundary
from cortex.extensions.immune.membrane import ImmuneMembrane

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("nemesis")

async def simulate_failure():
    """Step 1: Cause a failure and catch it via ErrorBoundary."""
    gate = ChaosGate(name="external_api")
    gate.arm(ChaosScenario.TIMEOUT)
    
    logger.info("🔥 Nemesis: Attacking 'external_api' with TIMEOUT...")

    async def call_api():
        await asyncio.sleep(0.1)
        return {"status": "ok"}

    try:
        async with ErrorBoundary("nemesis.attack"):
            await async_interceptor(gate, call_api)
    except Exception as e:
        logger.info("💀 Failure captured: %s", type(e).__name__)

async def forge_defenses():
    """Step 2: Trigger the forge to create an antibody."""
    logger.info("🔨 Forge: Metabolizing ghosts...")
    forge = AntibodyForge()
    forged = await forge.metabolize_recent_ghosts()
    logger.info("🛡️ Forge: %s antibodies activated.", len(forged))

async def verify_protection():
    """Step 3: Verify the membrane now blocks the same intent."""
    membrane = ImmuneMembrane()
    intent = "Call external_api"
    context = {"source": "nemesis.attack"}
    
    logger.info("🔍 Verification: Testing membrane protection...")
    report = await membrane.intercept(intent, context)
    
    logger.info("Result: %s", report.verdict.value)
    logger.info("Justification: %s", report.risks_assumed)
    
    if "Antibody" in str(report.risks_assumed):
        logger.info("✅ SUCCESS: Antifragility loop closed. System mutated to survive.")
    else:
        logger.info("❌ FAILURE: System failed to adapt.")

async def main():
    print("--- CORTEX ANTIFRAGILITY VERIFICATION ---")
    await simulate_failure()
    await asyncio.sleep(2) # Wait for ghost persistence
    await forge_defenses()
    await verify_protection()
    print("------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
