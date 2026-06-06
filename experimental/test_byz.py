# [C5-REAL] Exergy-Maximized
import asyncio
from cortex.extensions.swarm.byzantine import ByzantineConsensus

async def run():
    c = ByzantineConsensus()
    c.register_node("1")
    c.register_node("2")
    c.register_node("3")
    res = await c.execute_consensus({"1": "foo", "2": "foo", "3": "bar"})
    print("res:", res, type(res))

asyncio.run(run())
