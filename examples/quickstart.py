"""CORTEX quickstart for the currently supported source-install workflow.

Usage:
    git clone https://github.com/borjamoskv/Cortex-Persist.git
    cd Cortex-Persist
    pip install -e ".[api]"
    uvicorn cortex.api:app --port 8000
    python examples/quickstart.py

For the CLI-first trust proof, see docs/canonical-demo.md.
"""

from cortex_persist import CortexClient

client = CortexClient(base_url="http://localhost:8000")

# 1. Store a fact
client.store(
    content="CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.",
    fact_type="knowledge",
    project="demo",
)
print("✅ Fact stored")

# 2. Search by semantic similarity
results = client.search("What is CORTEX?", k=3, project="demo")
for r in results:
    print(f"  [#{r.id}] (score: {r.score:.3f}) {r.content[:80]}")

# 3. Check engine status
status = client.status()
print(f"\n🔎 Engine status: {status}")

print("\n🎉 CORTEX is operational!")
client.close()
