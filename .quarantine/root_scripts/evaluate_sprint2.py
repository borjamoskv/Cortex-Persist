# [C5-REAL] Exergy-Maximized
import sys
import asyncio

from cortex.engine import CortexEngine
from cortex.interfaces.memory_provider import MemoryProvider, MemoryResult, MemoryRef
from cortex.pipeline.triage import IssueTriagePipeline


class CortexMemoryProvider(MemoryProvider):
    def __init__(self, engine: CortexEngine):
        self.engine = engine
        self._loop = asyncio.get_event_loop()

    def search(self, query: str, limit: int = 10) -> list[MemoryRef]:
        # PHASE 1: Retrieval (we just extract metadata, even if engine decrypts, we ignore it)
        results = self._loop.run_until_complete(self.engine.search(query=query, top_k=limit))

        refs = []
        for r in results or []:
            refs.append(
                MemoryRef(
                    id=str(getattr(r, "id", "unknown")),
                    score=getattr(r, "score", 0.0) or getattr(r, "relevance", 0.0),
                    summary=getattr(r, "summary", ""),
                    fact_type=getattr(r, "fact_type", getattr(r, "type", "knowledge")),
                )
            )
        return refs

    def hydrate(self, refs: list[MemoryRef]) -> list[MemoryResult]:
        # PHASE 4: Hydration (DECRYPT ONLY HERE)
        hydrated = []
        for ref in refs:
            try:
                # We use the engine's get_fact method to hydrate and decrypt
                fact = self._loop.run_until_complete(self.engine.get_fact(int(ref.id)))
                if fact:
                    hydrated.append(MemoryResult(ref=ref, content=fact.content))
                else:
                    hydrated.append(MemoryResult(ref=ref, content="<Fact not found>"))
            except Exception as e:
                hydrated.append(MemoryResult(ref=ref, content=f"<Decryption/Fetch Error: {e}>"))
        return hydrated


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
        "https://github.com/borjamoskv/Cortex-Persist/issues/398",
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
                print(
                    f"  [{i + 1}] Score: {mem.ref.score:.2f} | Type: {mem.ref.fact_type} | Content: {mem.content[:60]}..."
                )

        except Exception as e:
            print(f"FAILED: {e}")

    # Cleanup
    loop.run_until_complete(engine.close())


if __name__ == "__main__":
    main()
