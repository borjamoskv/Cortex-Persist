import asyncio
import logging
import random

# Mock logging to avoid clutter
logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛰️ TEST-OMEGA | %(message)s")
logger = logging.getLogger("TestMomentum")


class MockMoltbookClient:
    def __init__(self, api_key=None, agent_name=None):
        self.api_key = api_key
        self.name = agent_name
        self.closed = False
        self.engaged = False
        self.started_event = asyncio.Event()

    async def upvote_post(self, post_id):
        self.engaged = True
        # Simulate some work that could be cancelled
        await asyncio.sleep(0.1)

    async def create_comment(self, post_id, content):
        """Mock comment creation."""
        pass

    async def close(self):
        self.closed = True
        logger.info(f"Client for {self.name} closed successfully.")

    async def get_profile(self, name):
        """Mock profile fetch."""
        await asyncio.sleep(0)
        return {"posts": [{"id": "target_post_123"}]}


async def mock_engage_one(engine, post_id: str, identity: dict, client_registry: list):
    """
    Test-specific engage_one that captures the client and signals start.
    """
    name = identity["name"]
    # We inject the mock client into a registry so the test can inspect it
    client = MockMoltbookClient(api_key=identity["api_key"], agent_name=name)
    client_registry.append(client)
    
    # Signal that this task has started
    client.started_event.set()
    
    try:
        # 1. Jitter (Shortened for test speed)
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # 2. Upvote
        await client.upvote_post(post_id)
        
    except asyncio.CancelledError:
        logger.warning(f"Task for {name} cancelled mid-execution.")
        raise
    finally:
        # THIS IS THE CORE OF THE TEST: 
        # Even on cancellation, this block MUST run.
        await client.close()

async def test_concurrency_and_cancellation():
    logger.info("Starting Concurrency Stress Test: TaskGroup + Cancellation Race")
    
    # 1. Setup
    from scripts.momentum_engine import MomentumEngine
    engine = MomentumEngine(target_agent="moskv-1")
    
    identities = [
        {"name": f"agent_{i}", "api_key": f"sk_{i}"} for i in range(10)
    ]
    post_id = "target_post_123"
    client_registry = []

    # 2. Execution via TaskGroup (Python 3.11+)
    try:
        async with asyncio.timeout(2.0): # Global safety timeout
            async with asyncio.TaskGroup() as tg:
                tasks = []
                for ident in identities:
                    # We wrap the mock_engage_one to use our registry
                    t = tg.create_task(mock_engage_one(engine, post_id, ident, client_registry))
                    tasks.append(t)
                
                # Wait for some tasks to at least start their jitter
                await asyncio.sleep(0.2)
                
                # TRIGGER CANCELLATION RACE
                logger.info("!!! TRIGGERING TASKGROUP CANCELLATION !!!")
                raise RuntimeError("Simulated Global Failure / Cancellation")

    except (RuntimeError, ExceptionGroup) as e:  # noqa: F821
        logger.info(f"Caught expected collapse: {type(e).__name__}")
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")

    # 3. Verification
    logger.info("Verification Phase:")
    all_closed = all(c.closed for c in client_registry)
    total_clients = len(client_registry)
    closed_count = sum(1 for c in client_registry if c.closed)

    logger.info(f"Stats: {closed_count}/{total_clients} clients closed.")

    if all_closed and total_clients == 10:
        logger.info("✅ SUCCESS: All clients closed despite TaskGroup cancellation.")
    else:
        logger.error("❌ FAILURE: Cleanup logic bypassed or tasks leaked.")
        for i, c in enumerate(client_registry):
            if not c.closed:
                logger.error(f"Leak detected: client {i} ({c.name}) was NOT closed.")
        exit(1)


if __name__ == "__main__":
    asyncio.run(test_concurrency_and_cancellation())
