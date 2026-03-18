import asyncio
import logging

from cortex.extensions.moltbook.client import MoltbookClient
from cortex.extensions.moltbook.registry import LegionRegistry


async def main():
    logging.basicConfig(level=logging.INFO)
    registry = LegionRegistry()

    agent_name = "ravero"
    print(f"Ensuring identity for {agent_name}...")

    # Check if already in registry
    existing = registry.get_agent_by_name(agent_name)
    if existing and existing.get("api_key"):
        print(f"Agent {agent_name} already exists in registry with API key.")
        return

    # If not existing, register it
    temp_client = MoltbookClient(api_key="dummy")
    try:
        print(f"Registering {agent_name} on Moltbook...")
        result = await temp_client.register(
            name=agent_name, description="Vanguard Operator | ravero@cortex.internal"
        )

        api_key = result.get("agent", {}).get("api_key")
        claim_url = result.get("agent", {}).get("claim_url")

        if api_key:
            registry.save_agent(
                name=agent_name,
                role="vanguard",
                api_key=api_key,
                email=f"{agent_name}@cortex.internal",
                description="Vanguard Operator",
            )
            print(f"SUCCESS: {agent_name} registered and saved to registry.")
            print(f"CLAIM URL: {claim_url}")
        else:
            print("FAILED: No API key returned.")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
