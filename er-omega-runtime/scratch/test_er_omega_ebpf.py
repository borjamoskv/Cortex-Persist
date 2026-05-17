import asyncio
from eromega.runtime_colonization import RuntimeColonizer


async def main():
    print("Starting ER-Ω.X Test (C5-REAL Simulation)...")
    colonizer = RuntimeColonizer(target_id="test-target", target_pid=1234)

    # Ejecutar colonización por 15 segundos
    try:
        await asyncio.wait_for(colonizer.colonize(), timeout=15)
    except asyncio.TimeoutError:
        print("Test completed successfully after 15s.")


if __name__ == "__main__":
    asyncio.run(main())
