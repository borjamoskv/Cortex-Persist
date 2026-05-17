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
logger = logging.getLogger("test_sentinel")


async def setup_test_data(ledger: SovereignLedger):
    """Populates the ledger with sub-optimal patterns for detection."""
    logger.info("Setting up sub-optimal test patterns in ledger...")

    tenant_id = "test_tenant"

    # 1. Add 6 grep calls (Redundant Grep pattern)
    for i in range(6):
        await ledger.record_transaction_async(
            project="test_proj",
            action="RUN_COMMAND",
            detail=f"grep -r 'SovereignLedger' . (call {i})",
            tenant_id=tenant_id,
        )

    # 2. Add 20 generic calls (Missing Thinking Mode pattern)
    for i in range(20):
        await ledger.record_transaction_async(
            project="test_proj",
            action="GENERIC_ACTION",
            detail=f"Action sequence step {i}",
            tenant_id=tenant_id,
        )


async def test_sentinel():
    # 1. Initialize DB and Ledger
    db_path = "test_sentinel.db"

    # Cleanup old test db if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()

    ledger = SovereignLedger(pool)
    await ledger.ensure_schema_async()

    # 2. Setup "Bad" Data
    await setup_test_data(ledger)

    # 3. Initialize the Sentinel Advisor
    advisor = CortexAdvisor(ledger)

    # 4. Analyze
    insights = await advisor.analyze_session(tenant_id="test_tenant")

    print("\n" + "=" * 50)
    print("🛡️  CORTEX-SENTINEL ADVISORY REPORT")
    print("=" * 50)

    if not insights:
        print("No sub-optimal patterns detected. System operating at peak yield.")

    for insight in insights:
        print(f"\n[TYPE]  {insight['type']}")
        print(f"[TITLE] {insight['title']}")
        print(f"[ADVICE] {insight['message']}")
        print(f"[AXIOM] {insight['axiom']}")

    # 5. Persist
    await advisor.persist_advice(insights, tenant_id="test_tenant")

    print("\n" + "=" * 50)
    print("✅ Advice persisted to Ledger. It will be recalled next session.")
    print("=" * 50)

    await pool.close()


if __name__ == "__main__":
    asyncio.run(test_sentinel())
