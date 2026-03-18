import asyncio
import os
import sys

# Ensure we can import from local cortex
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cortex.auth.manager import AuthManager


async def create_agent_key():
    auth_manager = AuthManager()
    await auth_manager.initialize()

    name = "antigravity-agent"
    raw_key, api_key = await auth_manager.create_key(
        name=name, role="admin", permissions=["read", "write", "admin"]
    )

    print(f"Key Name: {name}")
    print(f"Raw Key:  {raw_key}")
    print(f"Prefix:   {api_key.key_prefix}")

    await auth_manager.close()


if __name__ == "__main__":
    asyncio.run(create_agent_key())
