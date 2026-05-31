import asyncio
import logging
import os
from cortex.memory.manager import CortexMemoryManager
from cortex.extensions.policy.memory_os import MemoryOS


logging.basicConfig(level=logging.INFO)

async def run_resonance():
    print("[E2E] Booting MemoryOS...")
    # Initialize MemoryOS with in-memory SQLite for speed/safety
    os.environ["CORTEX_DB_URL"] = "sqlite+aiosqlite:///:memory:"
    
    os_kernel = MemoryOS()
    await os_kernel.start()
    
    manager = CortexMemoryManager()
    
    print("[E2E] Injecting Semantic Pulse...")
    response = await manager.process_interaction(
        role="user",
        content="This is a test of the decoupled Exergy pipeline.",
        session_id="e2e_session",
        tenant_id="e2e_tenant",
        project_id="e2e_project",
        token_count=15
    )
    
    print(f"[E2E] Pipeline Response: {response}")
    
    print("[E2E] Waiting for Glial Background Compression...")
    await manager.wait_for_background(timeout=3.0)
    
    print("[E2E] Shutting down OS...")
    await os_kernel.stop()
    print("[E2E] C5-REAL Success.")

if __name__ == "__main__":
    asyncio.run(run_resonance())
