import asyncio
from cortex.extensions.swarm.centauro_engine import CentauroEngine, Formation

async def run():
    print("Starting engine")
    engine = CentauroEngine()
    print("Engaging Yolo")
    result = await asyncio.wait_for(engine.engage("YOLO", formation=Formation.BLITZ), timeout=3.0)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(run())
