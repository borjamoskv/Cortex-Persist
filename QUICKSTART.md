# BABYLON-60-Persist Quickstart

A tamper-evident, sovereign memory engine for autonomous AI systems. This guide will get you up and running locally in under 3 minutes.

## 1. Installation

Install BABYLON-60 via pip. Python 3.10+ is required.

```bash
pip install babylon60
```

*(For Node.js/TypeScript users, the local HTTP server provides a standard REST API).*

## 2. Start the Local Memory Server

BABYLON-60 runs locally as a fast API server powered by SQLite and Vector embeddings.

```bash
# Initialize the database and start the server on port 8000
uvicorn cortex.api:app --reload
```

## 3. Store and Retrieve Facts (Python)

Once the server is running, you can connect your agents or scripts to it.

```python
from cortex import CortexClient

# Connect to local server
client = CortexClient(base_url="http://localhost:8000")

# 1. Store a memory (fact)
fact = client.store(
    content="The API key for production is strictly rotated every 30 days.",
    fact_type="knowledge",
    project="demo-app"
)
print(f"Fact stored securely with ID: {fact.id}")

# 2. Search memories semantically
results = client.search("How often do we rotate keys?", top_k=1)
for r in results:
    print(f"Found: {r.content} (Score: {r.score})")
```

## 4. Next Steps

- **[Full Tutorial](docs/tutorials/01_getting_started.md)**: Build your first complete agent integration.
- **[REST API Docs](http://localhost:8000/docs)**: View the Swagger UI while the server is running.
- **Interactive Scripts**: See the `examples/` directory for full examples with LangChain and basic flows.
