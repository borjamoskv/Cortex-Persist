import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cortex.swarm.specialists import GoogleJulesOmega

async def main():
    actuator = GoogleJulesOmega()
    task = "Integrate the Model Context Protocol (MCP) into Golem Cloud's CLI as per the $3,500 algora bounty requirements."
    context = {
        "repo": "golemcloud/golem",
        "branch": "main",
        "expected_yield_usd": 3500.0,
        "confidence": 0.85
    }
    
    print(f"Dispatching Jules to {context['repo']}...")
    try:
        response = await actuator.execute(task, context)
        print("Response Status:", response.status)
        print("Response Content:\n", response["content"])
        print("Response Metadata:\n", response["metadata"])
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    asyncio.run(main())
