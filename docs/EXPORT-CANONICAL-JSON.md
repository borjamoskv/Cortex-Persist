# RFC: SORTU-Ω Canonical Export Format v0.1
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14
Audience: Compliance Integrators, Core Engineers, Swarm Auditors

---

## 1. Purpose

The CORTEX Master Ledger must be portable. Lock-in is entropic; sovereignty requires exit guarantees.

This document defines the **Canonical JSON Export Format** (`EXPORT-CANONICAL-JSON`). This shape represents a snapshot of the trust, memory, and causality state of the system at an exact `as_of` instant.

By defining an exact stable representation before attempting to map to external standards (JSON-LD, SARIF, local LLM wrappers), we establish an immutable source of truth that ensures compliance teams and audits have mathematically rigorous material.

---

## 2. Design Principles

### 2.1 Complete Causal Fidelity
The export MUST contain the exact DAG (Directed Acyclic Graph) of causation required to reconstruct a decision. If Fact C came from Fact B, that edge must be in the export.

### 2.2 Recomputable Integrity
Any auditor with the exported JSON and the public cryptographic hashing algorithms MUST be able to recompute the hashes and prove the ledger was not tampered with.

### 2.3 Dialect Agnosticism
This is canonical internal truth. Adapters (e.g., to EU AI Act compliance formats, or RAG ingestion chunks) must be pure functions reading *from* this structure, never modifying the export itself.

---

## 3. Top-Level Envelope

Every export is a JSON sequence or a singular JSON artifact wrapped in `.cortex_export`. 

```json
{
  "$schema": "https://cortex.sovereign/schemas/v1/export.json",
  "export_id": "exp_8a91bf20",
  "schema_version": "1.0",
  "as_of": "2026-03-14T10:00:00Z",
  "tenant_id": "tenant_01",
  "project": "cortex-persist",
  "system_health_at_export": {
    "status": "ok",
    "degraded_features": []
  },
  "signature": "sha256:d8b2e3... (optional cryptographic seal of the payload)",
  "payload": {
    "facts": [],
    "causal_edges": [],
    "ledger_blocks": [],
    "agents": []
  }
}
```

---

## 4. Subsystem Layouts

### 4.1 Facts (Memory & Decisions)

Facts are the atomic assertions within the system.

```json
{
  "fact_id": "fact_001",
  "content": "The system detected a metastability drift in module X.",
  "confidence": 0.95,
  "is_tombstoned": false,
  "taint_state": {
    "status": "none",
    "reason": "Clear upstream track."
  },
  "provenance": {
    "source": "memory",
    "agent_id": "agent_nyx",
    "timestamp": "2026-03-14T09:45:00Z",
    "evidence_level": "traceable"
  },
  "hash": "sha256:abcd..."
}
```

### 4.2 Causal Edges (The Trace)

The trace exposes exactly how the system concluded the facts. No edge means the fact is an axiom (or an orphan hallucination).

```json
{
  "edge_id": "edge_001",
  "source_id": "fact_000",
  "target_id": "fact_001",
  "relationship": "derives_from",
  "operation_id": "op_xyz",
  "weight": 1.0
}
```
*Note: `source_id` is the parent (cause), `target_id` is the child (effect).*

### 4.3 Ledger Blocks (Integrity)

The immutable cryptographically chained sequence.

```json
{
  "block_idx": 44,
  "block_hash": "sha256:11bb22cc...",
  "previous_block_hash": "sha256:00aa11bb...",
  "merkle_root": "sha256:99dd88...",
  "timestamp": "2026-03-14T09:50:00Z",
  "contained_txs": ["tx_1", "tx_2"]
}
```

### 4.4 Agent Registry (Coordination)

The active actors that shaped the snapshot.

```json
{
  "agent_id": "agent_nyx",
  "tier": "sovereign",
  "capabilities": ["chaos", "inspection"],
  "last_liveness": "2026-03-14T09:55:00Z",
  "status": "active"
}
```

---

## 5. Parsing & Hydration Requirements

If a consumer wishes to **hydrate** a new CORTEX cluster using this export (working memory migration):
1. Hydration MUST enforce validation against `ledger_blocks`. Any fact missing from a block transaction is rejected.
2. Tombstoned facts (`is_tombstoned: true`) MUST NOT be resurrected into active working queries during hydration.
3. If `system_health_at_export` was `degraded`, the receiving CORTEX cluster must flag the imported module with an `import_degraded` warning.

---

## 6. Adapters (Post-Canonical Translations)

The architecture deliberately isolates translations:

- **JSON-LD**: For linked-data semantic web integrations. Generates `@context` and URIs mapping over `fact_id` and `edge_id`.
- **EU AI Act Reports**: Summarizes the schema specifically traversing the `taint_state` and `causal_edges` to prove "human oversight traceability" and "transparency of derivation" (Article 13).
- **SARIF**: (For `nyx-redteam-omega` or `mejoralo` outputs) Maps failed integrity/taint checks to security incident reports.
