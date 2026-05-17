import asyncio
from cortex.agents.builtins.centurion_agent import CenturionAgent, create_manifest


class MockBus:
    async def receive(self, *args, **kwargs):
        return None

    async def send(self, msg):
        print(f"Bus send: {msg.kind}")


async def run_strike():
    print("🚀 Running Centurion Strike...")
    agent = CenturionAgent(create_manifest(), MockBus())
    await agent.on_start()

    print("🔍 Auditing repository...")
    audit = await agent.audit_repository()

    print(f"\nFinal Score: {audit.score}")
    print(f"Grade: {audit.grade}")
    print(f"Issues: {audit.issues}")

    await agent._persist_audit(audit)
    print("\nReport generated at .cortex/repo_excellence_report.md")


if __name__ == "__main__":
    asyncio.run(run_strike())
