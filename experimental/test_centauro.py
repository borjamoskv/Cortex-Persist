import asyncio
from cortex.swarm.centauro_engine import CentauroEngine, Formation

async def run():
    engine = CentauroEngine()
    result = await engine.engage("YOLO", formation=Formation.BLITZ)
    print(result)

if __name__ == "__main__":
    asyncio.run(run())
