import asyncio
import sqlite3

import aiosqlite

_orig = sqlite3.connect

def _patched(*args, **kwargs):
    raise RuntimeError("Forbidden")

sqlite3.connect = _patched

async def main():
    try:
        async with aiosqlite.connect(":memory:") as db:
            await db.execute("SELECT 1")
    except Exception as e:
        print("aiosqlite failed:", e)

asyncio.run(main())
