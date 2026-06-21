# [C5-REAL] Exergy-Maximized
"""
CORTEX - C5-Dynamic Proof for AX-VIII (Stochastic Obsolescence).
Demonstrates the CausalClosureGuard intercepting Anergy in the Squadron phase.
"""

import asyncio
import logging

from cortex.engine.legion import Squadron, SwarmAgent, SwarmSignal

setup_cortex_logging()
logger = logging.getLogger("AX8-Simulator")


class MockAgent(SwarmAgent):
    async def execute(self, target: str) -> SwarmSignal:
        return SwarmSignal("Agent-1", target, "SUCCESS", {"response": target}, {})


class TestSquadron(Squadron):
    SQUAD_NAME = "TEST-PHALANX"

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return MockAgent(agent_id, self.bus, self.engine)


async def run_simulation():
    squadron = TestSquadron()

    logger.info("==================================================")
    logger.info("⚔️  SIMULATION 1: Limerent Swarm (Anergy Generation)")
    logger.info("==================================================")
    # Mocking signals that only contain narrative text
    limerent_signals = [
        SwarmSignal(
            "Agent-1",
            "target_1",
            "SUCCESS",
            {"response": "The swarm believes we should act carefully. No code synthesized."},
            {},
        ),
        SwarmSignal(
            "Agent-2",
            "target_2",
            "SUCCESS",
            {"response": "I agree with Agent-1, let's keep analyzing the problem space."},
            {},
        ),
    ]

    try:
        await squadron._crystallize(limerent_signals)
        logger.error("❌ FAILURE: Limerent swarm bypassed the guard! Axiom VIII violated.")
    except RuntimeError as e:
        logger.info("✅ SUCCESS (SAGA-1 ABORT DETECTED):")
        logger.info(f"   Exception caught: {e}")
        logger.info("   The Swarm was correctly murdered for producing pure Anergy.\n")

    logger.info("==================================================")
    logger.info("⚔️  SIMULATION 2: Crystallizing Swarm (Exergy Generation)")
    logger.info("==================================================")
    # Mocking signals that contain deterministic invariants (code)
    crystallizing_signals = [
        SwarmSignal(
            "Agent-1",
            "target_1",
            "SUCCESS",
            {
                "response": "We have synthesized the invariant:\n```python\ndef is_valid(): return True\n```"
            },
            {},
        ),
    ]

    try:
        report = await squadron._crystallize(crystallizing_signals)
        logger.info("✅ SUCCESS (CAUSAL CLOSURE ACHIEVED):")
        logger.info(f"   Squadron execution authorized. Report: {report}")
    except RuntimeError as e:
        logger.error(f"❌ FAILURE: Valid crystallization was blocked! Error: {e}")


if __name__ == "__main__":
    asyncio.run(run_simulation())
