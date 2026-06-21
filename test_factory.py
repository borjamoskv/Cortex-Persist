import aiosqlite
import asyncio
import sqlite3

class SovereignConnection(sqlite3.Connection):
    def set_authorizer(self, cb):
        raise Exception('blocked')

async def main():
    async with aiosqlite.connect(':memory:', factory=SovereignConnection) as db:
        await db._execute(lambda c: c.set_authorizer(None), db._conn)

asyncio.run(main())
