import asyncio
import aiosqlite
import os


async def main():
    conn = await aiosqlite.connect("scratch/test_ledger.db")
    print("Before:", os.path.getsize("scratch/test_ledger.db"))
    try:
        await conn.executescript("VACUUM;")
        print("VACUUM completed successfully")
    except Exception as e:
        print("Error during VACUUM:", e)
    print("After:", os.path.getsize("scratch/test_ledger.db"))
    await conn.close()


asyncio.run(main())
