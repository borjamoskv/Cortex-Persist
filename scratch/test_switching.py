import asyncio
import os
import sys

# Ensure cortex is in path
sys.path.append(os.getcwd())

from cortex.audit.advisor import CortexAdvisor
from cortex.engine import CortexEngine


async def test_context_switching():
    print("Testing Sentinel: High Context Switching Detection...")
    engine = CortexEngine()
    await engine.initialize()
    advisor = CortexAdvisor(engine.ledger)
    tenant = "test_switching"

    # 1. Simulate high context switching (5 unique files in 10 operations)
    print("Simulating high context switching...")
    files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
    for i in range(10):
        await engine.ledger.record_transaction_async(
            project="TEST",
            action="VIEW_FILE",
            detail={"TargetFile": files[i % 5]},
            tenant_id=tenant,
        )

    # 2. Run analysis
    insights = await advisor.analyze_session(tenant_id=tenant)

    found = False
    for insight in insights:
        if insight["title"] == "Reduce Context Switching":
            print(f"✔ Detected: {insight['message']}")
            found = True
            break

    if not found:
        print("❌ High Context Switching NOT detected.")

    await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(test_context_switching())
