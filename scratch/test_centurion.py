import asyncio
import logging
from cortex.agents.builtins.centurion_agent import CenturionAgent, create_manifest
from cortex.agents.message_schema import new_message, MessageKind

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("centurion_test")


class MockBus:
    async def receive(self, agent_id, timeout=1.0):
        return None

    async def send(self, msg):
        pass


async def test_centurion():
    # 1. Create agent
    manifest = create_manifest("test_centurion_01")
    bus = MockBus()
    agent = CenturionAgent(manifest, bus)

    logger.info("Starting CenturionAgent...")
    await agent.on_start()

    # 2. Run an audit manually
    logger.info("Running repository audit...")
    audit = await agent.audit_repository()

    print("\n--- REPO AUDIT RESULTS ---")
    print(f"Score: {audit.score * 100:.2f}%")
    print(f"Grade: {audit.grade}")
    print(f"Issues: {', '.join(audit.issues)}")
    print("\nRecommendations:")
    for rec in audit.recommendations:
        print(f"- {rec}")

    # 3. Simulate a message request for a proposal
    logger.info("\nRequesting improvement proposal...")
    msg = new_message(
        sender="human_user",
        recipient="test_centurion_01",
        kind=MessageKind.TASK_REQUEST,
        payload={"command": "proposal"},
    )

    # We need to mock the send_result to capture the output
    results = []

    async def mock_send_result(recipient, result, **kwargs):
        results.append(result)

    agent.send_result = mock_send_result
    await agent.handle_message(msg)

    if results:
        print("\n--- IMPROVEMENT PLAN ---")
        plan = results[0]
        print(f"Status: {plan['status']}")
        print(f"Priority Order: {', '.join(plan['priority_order'])}")
        print("\nActions:")
        for action in plan["actions"]:
            print(f"- {action}")

    # 4. Generate README patch
    logger.info("\nGenerating README patch...")
    patch = await agent.generate_readme_patch()
    print("\n--- README PATCH STATUS ---")
    print(f"Status: {patch['status']}")
    if "missing_sections" in patch:
        print("Missing sections detected:")
        for s in patch["missing_sections"]:
            print(f"- {s['heading']}: {s['reason']}")


if __name__ == "__main__":
    asyncio.run(test_centurion())
