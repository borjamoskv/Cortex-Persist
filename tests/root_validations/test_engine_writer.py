import asyncio

from cortex.engine import CortexEngine


async def main():
    engine = CortexEngine(db_path="test_assurance_crash.db")
    print("Type of engine.ledger_writer:", type(engine.ledger_writer))


if __name__ == "__main__":
    asyncio.run(main())
