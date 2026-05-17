import asyncio
from cortex.engine import CortexEngine


async def seed():
    engine = CortexEngine(db_path="cortex.db")

    # Facts to seed
    facts = [
        {
            "content": "The capital of France is Paris.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
        {
            "content": "Paris is known for the Eiffel Tower.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
        {
            "content": "The Eiffel Tower was built by Gustave Eiffel.",
            "fact_type": "history",
            "project_id": "geo",
        },
        {
            "content": "France is a country in Europe.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
        {
            "content": "Berlin is the capital of Germany.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
        {
            "content": "Germany is located in Central Europe.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
        {
            "content": "The Brandenburg Gate is a famous landmark in Berlin.",
            "fact_type": "knowledge",
            "project_id": "geo",
        },
    ]

    print("Seeding facts...")
    async with engine.session():
        print(f"Vector available: {engine._vec_available}")
        print(f"Memory ready: {engine._memory_ready}")
        print(f"Memory manager: {engine.memory}")

        if engine.memory is None:
            print(
                "ERROR: Memory manager is None. Subsystem might have initialized as partial (L1+L3 only)."
            )
            # If memory manager is None, we can't use .store() on it if it expects the manager.
            # However, StoreMixin also provides store(). Let's check where .store() comes from.

        for f in facts:
            # Try using engine.store if engine.memory is None, or just fail with more info
            fact_id = await engine.memory.store(
                content=f["content"],
                fact_type=f["fact_type"],
                project_id=f["project_id"],
                tenant_id="default",
            )
            print(f"Stored fact: {fact_id} -> {f['content']}")

    # Wait for background embedding if any (though store() usually waits for encode)
    if hasattr(engine.memory, "wait_for_background"):
        await engine.memory.wait_for_background()

    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
