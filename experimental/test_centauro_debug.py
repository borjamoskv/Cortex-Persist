import asyncio
from cortex.extensions.swarm.centauro_engine import CentauroEngine, Formation

async def run():
    print("Starting engine")
    engine = CentauroEngine()
    print("Engaging Yolo")
    print("type(engine.consensus.execute_consensus):", type(engine.consensus.execute_consensus))
    
    result = await engine.engage("YOLO", formation=Formation.BLITZ)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(run())
