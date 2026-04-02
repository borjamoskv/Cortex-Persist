import os
import json
import asyncio
import logging
import sqlite3
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import AsyncSignalBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.autopulse")

SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
STATE_FILE = "/tmp/cortex_state.json"

async def process_queue():
    """Background loop to consume and execute pending swarm tasks."""
    logger.info("Autopulse Engine: Ignited. Watching swarm queue...")
    
    while True:
        if os.path.exists(SWARM_QUEUE_FILE):
            try:
                with open(SWARM_QUEUE_FILE, "r") as f:
                    queue = json.load(f)
                
                pending = queue.get("pending_tasks", [])
                if pending:
                    task = pending.pop(0)
                    agent = task.get("agent", "Unknown")
                    payload = task.get("payload", {})
                    
                    logger.info(f"Autopoiesis: Processing task for {agent}...")
                    
                    # Update queue file
                    queue["pending_tasks"] = pending
                    with open(SWARM_QUEUE_FILE, "w") as f:
                        json.dump(queue, f, indent=2)
                    
                    # C5-REAL: Execution & OMEGA-X Epistemic Slashing
                    from cortex.swarm.tensor_glial import TensorGlialLegion
                    import hashlib
                    import time
                    
                    # Initialize massively parallel zero-copy 10k nodes
                    legion = TensorGlialLegion(num_agents=10000, d_dim=10000, file_path="/tmp/tensor_legion.vsa_mmap")
                    
                    # Apply biological decay (Fading Memory)
                    legion.apply_fading_memory(lambda_decay=0.01)
                    
                    # Log task action inside 1D Centurion 0
                    legion.batch_write_action([0], [f"Process: {payload}"])
                    
                    # Perform Fuzzing/Yield Epistemic Slashing
                    slashed = legion.epistemic_slash_and_respawn(bottom_percentile=10, elite_percentile=90)
                    if slashed > 0:
                        logger.info(f"OMEGA-X: Apoptosis activated. {slashed} dead nodes respawned from elite VSA topologies.")
                    
                    # Record the 'Success' in the Ledger
                    
                    # Get last hash from state file if possible
                    prev_hash = "GENESIS_BLOCK"
                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE, "r") as f:
                            state = json.load(f)
                            if state.get("ledgers"):
                                prev_hash = state["ledgers"][-1]["hash"]

                    action = f"SwarmSolve:{agent}"
                    vector_id = payload.get("vector_id", "swarm_task_auto")
                    yield_amount = 1.0  # Unit of Autopoiesis
                    timestamp = time.time()
                    
                    block_payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
                    block_hash = hashlib.sha256(block_payload.encode()).hexdigest()
                    
                    # Update State File
                    if not os.path.exists(STATE_FILE):
                        state = {"ledgers": []}
                    else:
                        with open(STATE_FILE, "r") as f:
                            state = json.load(f)
                    
                    state["ledgers"].append({
                        "timestamp": timestamp,
                        "action": action,
                        "vector_id": vector_id,
                        "yield_amount": yield_amount,
                        "hash": block_hash
                    })
                    
                    with open(STATE_FILE, "w") as f:
                        json.dump(state, f, indent=2)

                    # Emit Signal to Pulse (Dashboard)
                    try:
                        import aiosqlite
                        async with aiosqlite.connect(DB_PATH) as conn:
                            bus = AsyncSignalBus(conn)
                            await bus.emit("ledger_append", payload={
                                "hash": block_hash,
                                "action": action,
                                "vector_id": vector_id,
                                "yield_amount": yield_amount
                            })
                            logger.info(f"Autopulse: Ledger signal emitted for {block_hash[:8]}")
                    except Exception as e:
                        logger.error(f"Autopulse Signal Error: {e}")

            except Exception as e:
                logger.error(f"Autopulse Queue Error: {e}")
        
        await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(process_queue())
