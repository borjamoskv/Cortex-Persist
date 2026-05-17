import aiosqlite
import asyncio


async def f():
    async with aiosqlite.connect("scratch/test_ledger.db") as db:
        print("hasattr _path:", hasattr(db, "_path"))
        print("hasattr database:", hasattr(db, "database"))
        if hasattr(db, "_conn"):
            print("hasattr _conn:", hasattr(db._conn, "database"))


asyncio.run(f())
