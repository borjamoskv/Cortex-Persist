import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from cortex.cli.common import close_engine_sync, get_engine
from cortex.mejoralo import MejoraloEngine

logging.basicConfig(level=logging.INFO)


async def main():
    engine = get_engine("cortex.db")
    try:
        m = MejoraloEngine(engine)
        project = "cortex"
        path = Path(".")

        for i in range(1, 11):
            print(f"\n{'='*50}\n🚀 MEJORAlo YOLO Cycle {i}/10\n{'='*50}")

            # 1. Scan
            result = m.scan(project, path, brutal=True)
            print(f"📊 Score before: {result.score}/100")
            if result.score == 100:
                print("💎 Perfect score! Mission accomplished early.")
                break

            # 2. Heal explicitly targeting 100
            success = m.heal(project, path, 100, result)

            # 3. Post-scan
            result_after = m.scan(project, path, brutal=True)
            delta = result_after.score - result.score

            print(f"📈 Result: {result.score} -> {result_after.score} (Delta: {delta:+d})")
            print(f"✅ Success flag: {success}")

    finally:
        close_engine_sync(engine)


if __name__ == "__main__":
    asyncio.run(main())
