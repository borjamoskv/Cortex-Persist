import asyncio
import os

from cortex.engine import CortexEngine

async def main():
    import os
    db_path = "test_cb.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = CortexEngine(db_path=db_path)
    
    # Store decisions
    print("Storing 1 decision...")
    await engine.store("test_proj", "Decision 1", fact_type="decision", source="cli")
    
    # Store 1 ghosts -> Ghosts = 1, Decisions = 1 -> ED = 1 / 2 * 100 = 50%
    print("Storing 1 ghost...")
    await engine.store("test_proj", "Ghost 1", fact_type="ghost", source="cli")
    print("Storing 2nd ghost. This should trigger the breaker! (Ghosts = 2, Decisions = 1, ED = 100%)")
    
    try:
        await engine.store("test_proj", "Ghost 2", fact_type="ghost", source="cli")
        print("FAIL: Circuit Breaker did not trigger!")
    except RuntimeError as e:
        print(f"SUCCESS: Circuit Breaker triggered with message: {e}")
        
    # Check if the halt fact was created
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT fact_type, content, tags FROM facts WHERE tags LIKE '%circuit-break%'")
        row = await cursor.fetchone()
        if row:
            print(f"SUCCESS: Breaker Fact persisted: {row}")
        else:
            print("FAIL: Breaker Fact not persisted!")

if __name__ == "__main__":
    asyncio.run(main())
