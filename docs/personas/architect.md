# How Does CORTEX Sit in My Stack?

As an Enterprise Architect, your primary concern is scaling swarms of autonomous agents without ripping apart your existing infrastructure or introducing latency chokepoints.

CORTEX is a drop-in membrane designed specifically for coexistence.

## The Deployment Matrix

You choose where CORTEX lives based on your operational scale.

| Environment | Status | Storage / Topology | Description |
| :--- | :--- | :--- | :--- |
| **Local-First** | ✅ **Production-Ready** | SQLite + WAL + Vector | The core daemon. Runs in exactly one process. It has zero external dependencies and handles up to 10k agents on a single node concurrently. |
| **Self-Hosted** | 🟡 **Beta** | Multi-tenant + API | Instead of SDK `cortex store`, agents POST securely to an internal FastAPI gateway over HTTP. Connects to Redis. |
| **Sovereign Cloud** | ⏳ **v8.0 Target** | AlloyDB + Qdrant | Massive distribution via PostgreSQL clustering + Qdrant dedicated vectors to process swarm events globally. |

## The Tripartite Architecture

CORTEX uses a 3-layer ontology model. This is how you implement it alongside tools like Mem0, LangGraph, or Zapier:

1. **L1 (Working Memory):** High-latency loops inside your current agent. *Keep using Redis or purely transient dicts.*
2. **L2 (Semantic RAG):** The massive corpus of passive documents. *Keep using Pinecone, Qdrant, or Milvus here.*
3. **L3 (Episodic Ledger):** The immutable, tamper-evident record of actions and facts. **This is CORTEX.**

When your agent reaches a conclusion, mutates an external API, or definitively remembers a core user preference, you pass the artifact to `CortexEngine`.

[Read more on Stacks Integration](../integration_stacks.md)
