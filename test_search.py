import asyncio
from cortex.engine import CortexEngine

async def test():
    engine = CortexEngine()
    await engine.init_db() # Ensure extension loaded
    
    # Check if we have any facts
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT id, content FROM facts LIMIT 1")
        row = await cursor.fetchone()
        if not row:
            print("No facts found in DB")
            return
        fact_id, content = row
        print(f"Found fact {fact_id}: {content[:50]}...")
        
        # Test search
        results = await engine.search(query=content, top_k=5)
        print(f"Search results: {len(results)}")
        for r in results:
            print(f" - Found fact_id: {r.fact_id} (score: {r.score})")
            
    await engine.close()

if __name__ == "__main__":
    asyncio.run(test())
