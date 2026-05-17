import asyncio
import logging
import sys
import os

# Add root to sys.path for imports
sys.path.append(os.getcwd())

from cortex.ledger.ledger_core import SovereignLedger
from cortex.audit.advisor import CortexAdvisor
from cortex.database.pool import CortexConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_sentinel_recall")


async def test_recall():
    db_path = "test_sentinel.db"
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()

    ledger = SovereignLedger(pool)
    await ledger.ensure_schema_async()

    advisor = CortexAdvisor(ledger)

    # 1. First, analyze and persist (to have something to recall)
    # We use the data already in the DB from the previous test run
    insights = await advisor.analyze_session(tenant_id="test_tenant")
    await advisor.persist_advice(insights, tenant_id="test_tenant")

    # 2. Now Recall
    logger.info("Recalling advice from ledger...")
    recent_advice = await advisor.get_recent_advice(tenant_id="test_tenant", limit=2)

    print("\n" + "=" * 50)
    print("🧠 CORTEX-SENTINEL RECALL")
    print("=" * 50)

    for advice in recent_advice:
        print(f"\n[RECALL] {advice['title']}")
        print(f"Advice: {advice['message']}")

    print("\n" + "=" * 50)
    print("✅ Recall successful.")
    print("=" * 50)

    await pool.close()


if __name__ == "__main__":
    asyncio.run(test_recall())
