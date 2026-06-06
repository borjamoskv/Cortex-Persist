# [C5-REAL] Exergy-Maximized
from cortex.extensions.gate.ouroboros import get_ouroboros_gate
from cortex.engine import CortexEngine
import asyncio


async def run():
    engine = CortexEngine()
    gate = get_ouroboros_gate(engine)
    gate.trigger_pruning("treasury")
    print("Treasury pruned successfully.")


asyncio.run(run())
