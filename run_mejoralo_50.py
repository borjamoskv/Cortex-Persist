import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from cortex.cli.common import get_engine
from cortex.config import DEFAULT_DB_PATH
from cortex.mejoralo import MejoraloEngine

logging.basicConfig(level=logging.INFO)


async def main():
    engine = get_engine(DEFAULT_DB_PATH)
    try:
        m = MejoraloEngine(engine)
        project = "cortex"
        path = Path(".")

        cycles = 50
        for i in range(1, cycles + 1):
            print(f"\n{'='*50}\n🚀 MEJORAlo YOLO Cycle {i}/{cycles}\n{'='*50}")

            # 1. Scan
            result = m.scan(project, path, brutal=True)
            print(f"📊 Score before: {result.score}/100")
            if result.score >= 95:
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
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
