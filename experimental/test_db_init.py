import asyncio

from cortex.engine import CortexEngine


async def main():
    engine = CortexEngine("test_init.db")
    await engine.init_db()
    conn = await engine.get_conn()
    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in await cursor.fetchall()]
    print("TABLES:", tables)
    assert "entity_events" in tables, "entity_events missing!"
    await engine.close()


asyncio.run(main())
