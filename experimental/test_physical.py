import asyncio
import os
import time

from cortex.daemon.centaur.queue import EntropicQueue
from cortex.daemon.centaur.heartbeat import HeartbeatDaemon
from cortex.swarm.centauro_engine import CentauroEngine

async def test_physical():
    os.environ["CORTEX_NO_LLM"] = "1"
    
    print("Initializing CORTEX Physical Parity...")
    queue = EntropicQueue(db_path="test_entropic_queue.db")
    engine = CentauroEngine()
    
    # Push physical task
    task_id = queue.push(
        task_type="PHYSICAL",
        payload={"command": "echo 'Hello from CORTEX Physical Actuator!' && ls -l"},
        priority=10
    )
    print(f"Pushed PHYSICAL task {task_id}")
    
    heartbeat = HeartbeatDaemon(queue, engine, poll_interval=1.0)
    
    # Run daemon for 3 seconds to let it process
    task = asyncio.create_task(heartbeat.start())
    await asyncio.sleep(3)
    await heartbeat.stop()
    await task
    
    # Check status
    final_task = queue.db.execute("SELECT status FROM queue WHERE id = ?", (task_id,)).fetchone()
    print(f"\nFinal Task Status: {final_task[0] if final_task else 'Not Found'}")
    
    # Read iturria result to see stdout
    from pathlib import Path
    iturria_dir = Path.home() / ".cortex" / "iturria"
    files = list(iturria_dir.glob(f"PHYSICAL_*{task_id[:8]}*.md"))
    if files:
        latest = max(files, key=os.path.getctime)
        print("\n--- Iturria Output (Physical Parity Result) ---")
        print(latest.read_text())
    else:
        print("Dream Layer (Iturria) result not found.")
        
    # Cleanup
    if os.path.exists("test_entropic_queue.db"):
        os.remove("test_entropic_queue.db")

if __name__ == "__main__":
    asyncio.run(test_physical())
