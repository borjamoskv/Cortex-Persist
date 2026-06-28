import asyncio
import json
import os
import sqlite3
import time


async def main():
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    print(f"Connecting to {db_path}...")

    conn = sqlite3.connect(db_path)
    # Ensure table exists for safety
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            payload TEXT,
            status TEXT,
            priority INTEGER,
            created_at REAL
        )
    """)

    conn.execute("""
        INSERT OR REPLACE INTO tasks (id, payload, status, priority, created_at)
        VALUES (?, ?, 'pending', 7, ?)
    """, (
        "cascade-smoke-001",
        json.dumps({
            "type": "architecture",
            "prompt": "Refactor cascade_router.py: add async retry logic with exponential backoff per engine",
            "context_tokens": 4200,
            "target_engine": None  # forzar decisión del router
        }),
        time.time()
    ))
    conn.commit()
    print("Task injected successfully.")

    # Pull the task and route it.
    cursor = conn.execute("SELECT id, payload FROM tasks WHERE status='pending' LIMIT 1")
    row = cursor.fetchone()
    if row:
        task_id = row[0]
        payload = json.loads(row[1])
        
        # Update to processing
        conn.execute("UPDATE tasks SET status='processing' WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        
        print(f"Processing task {task_id}...")
        
        import sys
        sys.path.insert(0, "~/10_PROJECTS/cortex-persist")
        os.environ["PATH"] = f"~/10_PROJECTS/cortex-persist/tests/mock-bin:{os.environ.get('PATH', '')}"
        from cortex.engine.cascade_router import CascadeRouter
        
        router = CascadeRouter()
        result = await router.route_task(
            prompt=payload.get("prompt"),
            task_type=payload.get("type"),
            task_id=task_id
        )
        
        print("Result snippet:", result[:300])
        
        # Check task status in db after run by opening a new connection
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
        new_status = cursor.fetchone()[0]
        print(f"Post-execution Task Status in DB: {new_status}")
        conn.close()
    else:
        print("No pending tasks found.")

if __name__ == "__main__":
    asyncio.run(main())
