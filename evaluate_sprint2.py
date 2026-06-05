import sys
import asyncio
from typing import List
from cortex.engine import CortexEngine
from cortex.interfaces.memory_provider import MemoryProvider, MemoryResult
from cortex.pipeline.triage import IssueTriagePipeline

class CortexMemoryProvider(MemoryProvider):
    def __init__(self, engine: CortexEngine):
        self.engine = engine

    def search(self, query: str, limit: int = 10) -> List[MemoryResult]:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, we must adapt, but for this CLI it's fine
            raise RuntimeError("Cannot run sync search inside running event loop")
        
        # Call the real async search from CortexEngine
        results = loop.run_until_complete(self.engine.search(query=query, limit=limit))
        
        memories = []
        for r in (results or []):
            memories.append(MemoryResult(
                id=str(getattr(r, "id", "unknown")),
                score=getattr(r, "score", 0.0) or getattr(r, "relevance", 0.0),
                summary=getattr(r, "summary", ""),
                content=getattr(r, "content", str(r)),
                fact_type=getattr(r, "fact_type", getattr(r, "type", "knowledge"))
            ))
        return memories

async def setup_engine() -> CortexEngine:
    engine = CortexEngine("/tmp/cortex_copy.db")
    await engine.init_db()
    return engine

def main():
    test_urls = [
        "https://github.com/borjamoskv/Cortex-Persist/issues/415",
        "https://github.com/borjamoskv/Cortex-Persist/issues/414",
        "https://github.com/borjamoskv/Cortex-Persist/issues/413",
        "https://github.com/borjamoskv/Cortex-Persist/issues/412",
        "https://github.com/borjamoskv/Cortex-Persist/issues/411",
        "https://github.com/borjamoskv/Cortex-Persist/issues/402",
        "https://github.com/borjamoskv/Cortex-Persist/issues/401",
        "https://github.com/borjamoskv/Cortex-Persist/issues/400",
        "https://github.com/borjamoskv/Cortex-Persist/issues/399",
        "https://github.com/borjamoskv/Cortex-Persist/issues/398"
    ]
    
    # 1. Initialize Real CORTEX Engine
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = loop.run_until_complete(setup_engine())
    
    # 2. Wire the Pipeline
    provider = CortexMemoryProvider(engine)
    pipeline = IssueTriagePipeline(provider)
    
    # 3. Execute Gate
    for url in test_urls:
        print(f"\n[{url}]")
        try:
            context = pipeline.process(url)
            print(f"Title: {context.issue.title}")
            print(f"Body Length: {len(context.issue.body)}")
            print(f"Related Memories Retrieved: {len(context.related_memories)}")
            
            for i, mem in enumerate(context.related_memories):
                print(f"  [{i+1}] Score: {mem.score:.2f} | Type: {mem.fact_type} | Content: {mem.content[:60]}...")
                
        except Exception as e:
            print(f"FAILED: {e}")
            
    # Cleanup
    loop.run_until_complete(engine.close())

if __name__ == "__main__":
    main()
