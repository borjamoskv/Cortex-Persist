import asyncio
import os
import sys
import httpx

# Ensure we can import from local cortex
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from cortex.async_client import AsyncCortexClient

load_dotenv()


async def verify_codex():
    api_token= os.environ.get("CORTEX_API_KEY")
    # Force IPv4
    client = AsyncCortexClient(api_token=api_key, base_url="http://127.0.0.1:8000")

    try:
        # Recall recent facts to verify storage
        print("📜 Recalling recent facts...")
        results = await client.recall(project="cortex", limit=10)

        print(f"\n✨ Found {len(results)} active facts:")
        for res in results:
            print(f"\nFact #{res.id} ({res.fact_type}): {res.content[:100]}...")

    except (httpx.RequestError, ValueError, RuntimeError) as e:
        print(f"❌ Verification failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(verify_codex())
