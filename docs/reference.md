# Python API Reference

This section is auto-generated from the CORTEX Python source code using `mkdocstrings`.

For HTTP routes and request/response shapes, see the [REST API Reference](api.md).
For the public contract boundaries, see [SDK Surface](SDK-SURFACE.md), [Trust Semantics](TRUST-SEMANTICS.md),
[Event Model](EVENT-MODEL.md), and [Error Code Registry](ERROR-CODE-REGISTRY.md).

---

## Core Engine

The `CortexEngine` is the primary entry point for all CORTEX operations. It aggregates mixins for storage, querying, consensus, search, and graph operations.

::: cortex.engine.CortexEngine
    options:
      show_source: false
      members_order: source

## Async Route Engine

FastAPI, MCP, and other async contexts use `CortexEngine` with async methods and, where needed,
`CortexConnectionPool`. `AsyncCortexEngine` is currently a compatibility alias exported from
`cortex.engine`; there is no separate `cortex.engine_async` module in the live package.

::: cortex.engine.AsyncCortexEngine
    options:
      show_source: false

---

## Models & Entities

### Fact

The core data unit in CORTEX — a timestamped, hash-chained record of a decision, error, ghost, or knowledge entry.

::: cortex.engine.models.Fact

---

## Trust Layer

### Consensus Manager

Multi-agent Byzantine fault-tolerant (WBFT) fact verification. Agents vote on facts with reputation-weighted confidence.

::: cortex.consensus.manager.ConsensusManager
    options:
      show_source: false

### Privacy Mixin

Zero-leakage ingress guard with 11 secret detection patterns (API keys, tokens, passwords, etc.). Mixed into the engine.

::: cortex.engine.privacy_mixin.PrivacyMixin
    options:
      show_source: false

---

## Memory System

### Memory Manager

Orchestrates the tripartite memory system: L1 (Working) → L2 (Vector) → L3 (Episodic Ledger).

::: cortex.memory.manager.CortexMemoryManager
    options:
      show_source: false

### Embedding Manager

Manages vector embeddings for semantic search using SentenceTransformers or external providers.

::: cortex.embeddings.manager.EmbeddingManager
    options:
      show_source: false

---

## Security & Authentication

### Auth Manager

HMAC-SHA256 API key authentication with RBAC (4 roles: SYSTEM, ADMIN, AGENT, VIEWER).

::: cortex.auth.AuthManager
    options:
      show_source: false

### Sovereign Gate

Rate limiting, request approval workflows, and action-level security enforcement.

::: cortex.extensions.gate.core.SovereignGate
    options:
      show_source: false

---

## Platform Services

### Facts Manager

Low-level fact CRUD operations, delegation layer between engine and database.

::: cortex.facts.manager.FactManager
    options:
      show_source: false

### Daemon

Self-healing background daemon with 13 monitors (disk, memory, network, ghost, cert, etc.).

::: cortex.extensions.daemon.core.MoskvDaemon
    options:
      show_source: false
