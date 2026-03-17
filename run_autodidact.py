import asyncio
from cortex.skills.autodidact.synthesis import execute_cognitive_synthesis

async def run():
    with open("/tmp/paper.txt", "r") as f:
        raw_data = f.read()
        
    source = "https://aclanthology.org/2025.emnlp-main.1318.pdf?utm_source=chatgpt.com"
    intent = "Extract the hierarchical memory storage architecture (STM, MTM, LPM), segmented paging, and heat-based evaporation mechanisms (MemoryOS) as C4/C5 axioms."
    
    print(f"Running synthesis on {len(raw_data)} chars from {source}")
    memo_id = await execute_cognitive_synthesis(raw_data=raw_data, source=source, force=True, intent=intent)
    print(f"Synthesis complete. Memo ID: {memo_id}")

if __name__ == "__main__":
    asyncio.run(run())
