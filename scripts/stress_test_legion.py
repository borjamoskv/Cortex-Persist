import argparse
import asyncio
import sys
import time

from cortex.extensions.llm.router import CortexLLMRouter
from cortex.extensions.swarm.centauro_engine import CentauroEngine


async def run_mission(engine: CentauroEngine, mission_id: int, formation: str):
    print(f"[MISSION {mission_id}] Initiating...")
    start_time = time.time()
    try:
        result = await engine.engage(mission=f"Stress test task {mission_id}", formation=formation)
        elapsed = time.time() - start_time
        status = result.get("status")
        print(f"[MISSION {mission_id}] Completed in {elapsed:.2f}s | Status: {status}")
        return status
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[MISSION {mission_id}] FAILED in {elapsed:.2f}s | Error: {str(e)}")
        return "error"


async def main():
    parser = argparse.ArgumentParser(description="LEGIØN-1 Stress Test")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent missions")
    parser.add_argument("--formation", default="HYDRA", help="Tactical formation to deploy")
    parser.add_argument("--sim", action="store_true", help="Force C4-SIM mode (No LLM calls)")

    args = parser.parse_args()

    print(f"🔱 LEGIØN-1 STRESS TEST ACTIVATED")
    print(f"CONCURRENCY: {args.concurrency}")
    print(f"FORMATION: {args.formation}")
    print(f"MODE: {'C4-SIM' if args.sim else 'C5-REAL'}")

    if not args.sim:
        from cortex.extensions.llm.provider import LLMProvider
        primary_provider = LLMProvider("gemini")
        fallback_providers = [
            LLMProvider("openrouter"),
            LLMProvider("deepseek"),
            LLMProvider("ollama"),
            LLMProvider("lmstudio"),
        ]
        router = CortexLLMRouter(primary=primary_provider, fallbacks=fallback_providers)
    else:
        router = None

    engine = CentauroEngine(tolerance=0.67, router=router)

    start_time = time.time()
    tasks = [
        run_mission(engine, i, args.formation)
        for i in range(1, args.concurrency + 1)
    ]
    
    results = await asyncio.gather(*tasks)
    total_elapsed = time.time() - start_time

    successes = results.count("success")
    errors = results.count("error")

    print("\n[STRESS TEST RESULT]")
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"Successful missions: {successes}/{args.concurrency}")
    print(f"Failed missions: {errors}/{args.concurrency}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
