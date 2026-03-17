from cortex.daemon.centaur.queue import EntropicQueue
from cortex.daemon.centaur.heartbeat import HeartbeatDaemon
from cortex.swarm.centauro_engine import CentauroEngine
from pathlib import Path
import asyncio

async def test_all():
    db_path = Path("/tmp/test_entropic_queue.db")
    if db_path.exists():
        db_path.unlink()
    
    # 1. Test Queue
    queue = EntropicQueue(db_path)
    task_id = queue.push("RESEARCH", {"topic": "Autopoiesis in AI"}, priority=10)
    print(f"Pushed task: {task_id}")
    
    popped = queue.pop()
    print(f"Popped task: {popped}")
    assert popped["id"] == task_id
    
    # 2. Test Daemon instantiation
    engine = CentauroEngine()
    daemon = HeartbeatDaemon(queue, engine, poll_interval=1.0)
    print("Daemon instantiated successfully. Starting for 2 seconds...")
    
    task = asyncio.create_task(daemon.start())
    await asyncio.sleep(2.0)
    await daemon.stop()
    await task
    
    print("Daemon stopped. Task should be completed.")
    
    # Clean up
    if db_path.exists():
        db_path.unlink()
    shm = Path("/tmp/test_entropic_queue.db-shm")
    if shm.exists(): shm.unlink()
    wal = Path("/tmp/test_entropic_queue.db-wal")
    if wal.exists(): wal.unlink()

if __name__ == "__main__":
    asyncio.run(test_all())
