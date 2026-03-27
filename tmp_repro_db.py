import asyncio
import tempfile
import os
import sqlite3

from cortex.engine import CortexEngine

async def main():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        engine = CortexEngine(db_path=path, auto_embed=False)
        print("Calling init_db...")
        await engine.init_db()
        print("init_db finished.")
        
        # Check tables
        conn = sqlite3.connect(path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print(f"Tables in DB: {[t[0] for t in tables]}")
        conn.close()
        
        # Try store
        print("Storing fact...")
        await engine.store(content="test", project="test", fact_type="knowledge")
        print("Store succeeded.")
        await engine.close()
    finally:
        os.unlink(path)

if __name__ == "__main__":
    asyncio.run(main())
