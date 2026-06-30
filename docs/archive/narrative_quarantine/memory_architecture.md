# [C5-REAL] Tripartite Memory Architecture

BABYLON-60 enforces a strict **Tripartite Memory Architecture** to guarantee that probabilistic inputs (conjectures) are crystallized into deterministic, tamper-evident truths without saturating local resources or causing context rot.

## Overview

The memory hierarchy separates the lifecycle of a fact based on its thermodynamic footprint and epistemic certainty:

1. **L1: Working Memory (HOT)**
2. **L2: Vector Sink (WARM)**
3. **L3: Episodic Ledger (TRUTH / COLD)**

---

## L1: Working Memory (HOT)
**Implementation:** Redis / In-Memory `Dict`
**Purpose:** Stochastic context retention, temporary swarm states, and prompt staging.

L1 acts as the fluid, transient buffer where agents operate. It allows for high-throughput, lossy read/write cycles without burning cryptographic exergy.
- **Eviction:** Managed by the `LandauerDaemon`. Context that falls below the exergy threshold or remains unvalidated is aggressively purged (Apoptosis).
- **Isolation:** Strictly scoped by `tenant_id` and `conversation_id`.

## L2: Vector Sink (WARM)
**Implementation:** `sqlite-vec` (Local) / Turbopuffer (Cloud)
**Purpose:** Semantic search, embeddings, and similarity routing.

L2 stores the structural representation of knowledge. 
- **Immutable Dimensions:** Each model dimensionality requires its own virtual table (e.g., `cortex_embeddings_text` vs `cortex_embeddings_visual`).
- **Sync Safety:** Virtual `vec0` tables in SQLite do not support Foreign Keys. The `engine/store_mixin.py` orchestrates the insertion of the metadata first, immediately mapping the embedding via `last_insert_rowid()`.
- **Draining:** The `L2DrainMonitor` daemon periodically offloads cold vectors from local `sqlite-vec` to a remote vector database if configured, keeping the local index lean.

## L3: Episodic Ledger (TRUTH / COLD)
**Implementation:** SQLite (`WAL` mode) + Rust-backed `ZeroCopyRingBuffer`
**Purpose:** Cryptographic source of truth, audit trails, BFT consensus resolution.

L3 is the core of BABYLON-60's local-first persistence. Generative output is not considered "state" until it reaches L3.
- **Append-Only Hash Chain:** Every transaction is hashed with SHA-256 (`hash = SHA256(prev_hash + payload)`).
- **Merkle Checkpoints:** Batches of transactions are rolled into Merkle Trees for O(log N) integrity verification.
- **Concurrency:** Uses `BEGIN IMMEDIATE`, `busy_timeout=5000ms`, and strict connection serialization to prevent lock contention.

---

## Fact Lifecycle & SAGA Pattern

Data flows strictly in one direction through the Tripartite system:

`L1 (Conjecture)` ➜ `Guards (Validation)` ➜ `Taint Signature` ➜ `L3 (Ledger/Fact)` ➜ `L2 (Index)`

If any guard fails, the SAGA pattern triggers an immediate abort and backward compensation. The L3 Ledger logs the rejection, ensuring that malicious or hallucinated facts leave an audit trail without mutating the core facts table.

## Context Compression (Landauer's Principle)

To prevent the AI models from suffering "Context Rot," BABYLON-60 applies Thermodynamic Context Compression. Before loading episodic memory from L3 into L1 for an LLM prompt, the system extracts the structural invariants (JSON/YAML) and strips all conversational narrative.
