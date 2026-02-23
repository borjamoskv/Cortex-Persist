"""CORTEX Quickstart — Store, Search, Ask in 10 lines.

Usage:
    pip install cortex-memory
    export CORTEX_API_KEY=your_key
    python quickstart.py
"""

from cortex import CortexClient

client = CortexClient(base_url="http://localhost:8000")

# 1. Store a fact
client.store(
    content="CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.",
    fact_type="knowledge",
    project="demo",
)
print("✅ Fact stored")

# 2. Search by semantic similarity
results = client.search("What is CORTEX?", top_k=3)
for r in results:
    print(f"  [#{r.fact_id}] (score: {r.score:.3f}) {r.content[:80]}")

# 3. Ask with RAG (requires LLM provider configured)
try:
    import httpx

    resp = httpx.post(
        "http://localhost:8000/v1/ask",
        json={"query": "What is CORTEX?", "k": 5},
        headers={"X-API-Key": "your_key"},
    )
    print(f"\n🧠 Answer: {resp.json()['answer']}")
except Exception as e:
    print(f"\n⚠️ RAG requires LLM provider: {e}")

print("\n🎉 CORTEX is operational!")
