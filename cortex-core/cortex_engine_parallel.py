import os
import concurrent.futures
import time
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] CORTEX-PARALLEL: %(message)s")

class SwarmProcessPool:
    def __init__(self, max_workers=None):
        # By default, ProcessPoolExecutor will spawn as many workers as there are CPU cores (O(1) mapping per core)
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        # Using a dummy wrapper to extract the private max_workers var safely 
        limit = max_workers or os.cpu_count() or 4
        logging.info(f"SwarmProcessPool Initialized. Max Parallel Limits: {limit}")
        
    def submit_sync_task(self, target_function, *args, **kwargs):
        """Submit a CPU-bound or blocking request to the Parallel Worker Pool."""
        return self.executor.submit(target_function, *args, **kwargs)

    async def execute_in_parallel(self, loop, target_function, *args):
        """Standard AsyncIO wrapper to bypass GIL blocking operation in FastAPI/Event loops."""
        return await loop.run_in_executor(self.executor, target_function, *args)

    def shutdown(self):
        self.executor.shutdown(wait=True)
        logging.info("SwarmProcessPool Shutdown.")

# Expose a global Singleton for the MCP Server to import
ENGINE = SwarmProcessPool()
