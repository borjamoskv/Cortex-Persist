# [C5-REAL] Exergy-Maximized
import asyncio

from cortex.engine import CortexEngine
from cortex.extensions.gate.ouroboros import get_ouroboros_gate


async def run():
    engine = CortexEngine()
    gate = get_ouroboros_gate(engine)
    gate.trigger_pruning("treasury")
    print("Treasury pruned successfully.")


asyncio.run(run())
