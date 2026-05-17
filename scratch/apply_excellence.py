import asyncio
import logging
from cortex.agents.builtins.centurion_agent import CenturionAgent, create_manifest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("centurion_apply")


class MockBus:
    async def receive(self, agent_id, timeout=1.0):
        return None

    async def send(self, msg):
        pass


async def main():
    agent = CenturionAgent(create_manifest(), MockBus())
    await agent.on_start()

    # 1. Audit
    logger.info("Auditing repository...")
    audit = await agent.audit_repository()
    logger.info(f"Initial Score: {audit.score * 100:.2f}% ({audit.grade})")

    # 2. Propose
    logger.info("Generating proposals...")
    proposal = await agent.generate_proposal(audit)
    patches = proposal.get("patches", [])
    logger.info(f"Generated {len(patches)} patches.")

    # 3. Apply
    for p in patches:
        logger.info(f"Applying patch: {p['id']} ({p['type']})")
        result = await agent.apply_patch(p["id"])
        logger.info(f"Result: {result['status']}")

    # 4. Final Audit
    logger.info("Verifying improvements...")
    final_audit = await agent.audit_repository()
    logger.info(f"Final Score: {final_audit.score * 100:.2f}% ({final_audit.grade})")

    if final_audit.score > audit.score:
        logger.info("SUCCESS: Repository excellence improved!")
    else:
        logger.warning("No improvement detected in score.")


if __name__ == "__main__":
    asyncio.run(main())
