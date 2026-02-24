# Python API Reference

This section is auto-generated from the CORTEX Python source code using `mkdocstrings`.

---

## Core Engine

The `CortexEngine` is the primary entry point for all CORTEX operations. It aggregates mixins for storage, querying, consensus, search, and graph operations.

::: cortex.engine.CortexEngine
    options:
      show_source: false
      members_order: source

## Async Engine

Async-native engine for use in FastAPI, MCP, and other async contexts.

::: cortex.engine_async.AsyncCortexEngine
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

### Privacy Shield

Zero-leakage ingress guard with 11 secret detection patterns (API keys, tokens, passwords, etc.).

::: cortex.privacy.shield.PrivacyShield
    options:
      show_source: false

---

## Memory System

### Memory Manager

Orchestrates the tripartite memory system: L1 (Working) → L2 (Vector) → L3 (Episodic Ledger).

::: cortex.memory.manager.MemoryManager
    options:
      show_source: false

### Embedding Manager

Manages vector embeddings for semantic search using SentenceTransformers or external providers.

::: cortex.embeddings.manager.EmbeddingManager
    options:
      show_source: false

---

## Search & Retrieval

### Search Engine

Hybrid search combining vector similarity, keyword matching, and knowledge graph traversal.

::: cortex.search.engine.SearchEngine
    options:
      show_source: false

### Graph Module

Knowledge graph for entity relationships and decision lineage.

::: cortex.graph.manager.GraphManager
    options:
      show_source: false

---

## Security & Authentication

### Auth Manager

HMAC-SHA256 API key authentication with RBAC (4 roles: admin, operator, reader, agent).

::: cortex.auth.manager.AuthManager
    options:
      show_source: false

### Gate

Rate limiting, request validation, and security header enforcement.

::: cortex.gate.manager.GateManager
    options:
      show_source: false

---

## Platform Services

### Facts Manager

Low-level fact CRUD operations, delegation layer between engine and database.

::: cortex.facts.manager.FactManager
    options:
      show_source: false

### Daemon Controller

Self-healing background daemon with 13 monitors (disk, memory, network, ghost, cert, etc.).

::: cortex.daemon.core.DaemonController
    options:
      show_source: false

### Compaction

Intelligent compaction of old facts to reduce database size while preserving audit integrity.

::: cortex.compaction.manager.CompactionManager
    options:
      show_source: false
