import asyncio
import aiosqlite
import os


async def test():
    db_path = "scratch/test_async.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    try:
        conn = await aiosqlite.connect(db_path)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("CREATE TABLE test (id INTEGER)")
        await conn.commit()
        await conn.close()
        print("Success")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test())
