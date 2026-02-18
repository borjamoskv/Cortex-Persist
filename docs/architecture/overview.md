# CORTEX Architecture Overview

## The Core
Cortex is a **local-first, sovereign intelligence engine**. It is NOT a chatbot. It is an operating system for cognition.

### Components

1.  **The Memory (Lizard Brain)**
    -   **SQLite (`cortex.db`)**: The physical storage of facts.
    -   **Vector Store (`chromadb`)**: Semantic search and retrieval.
    -   **Graph (`networkx`)**: Relationships between entities (Code <-> Doc <-> Person).

2.  **The Engine (Prefrontal Cortex)**
    -   **`CortexEngine`**: The main interface. Handles ingestion, retrieval, and synthesis.
    -   **`ledger.py`**: Merkle-backed immutable log of all thoughts/actions.
    -   **`sovereign_gate.py`**: The firewall. Decides what enters long-term memory.

3.  **The Swarm (Nervous System)**
    -   **`dispatch.py`**: Routes tasks to specialized agents.
    -   **`adapter.py`**: Connects to external MCP tools (Git, Terminal, Browser).

## Data Flow

1.  **Ingestion**: `User Input` -> `Gate` -> `Vector Embed` -> `Graph Node` -> `Storage`.
2.  **Recall**: `Query` -> `Semantic Search` + `Graph Walk` -> `Context Assembly` -> `LLM`.
3.  **Action**: `Plan` -> `Swarm Dispatch` -> `Tool Execution` -> `Result` -> `Memory`.

## Key Invariants
-   **Local First**: No data leaves the machine unless explicitly authorized.
-   **Immutable**: History is never deleted, only appended (Ledger).
-   **Verifiable**: Every action has a Merkle proof.
