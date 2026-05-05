# RFC-001: The CORTEX Trust Verification Standard for AI Agent Memory

> **Sovereign Specification** · Status: DRAFT · Protocol v1.0.0 · CORTEX-Persist
> **Classification:** Draft RFC. This is normative proposal text, not a historical snapshot.

## 1. Abstract & Axiomatic Foundation

The current paradigm of AI agent memory relies on fundamentally flawed, probabilistic storage (Vector DBs) without cryptographic verification. This constitutes a critical vulnerability: memory without mathematical provenance is structurally indistinguishable from hallucination.

This document formally defines the **CORTEX Trust Verification Standard**, a protocol designed to elevate AI agent memory from probabilistic storage to a deterministic, tamper-evident cryptographic ledger. Any system claiming CORTEX compliance MUST implement the constraints, schemas, and pipelines outlined herein.

**Current implementation note:** the shipped `cortex-persist` package currently
uses SHA-256 for sovereign ledger continuity and Merkle lineage. Some audit or
signature-oriented subsystems also use SHA3-256, but that does not currently
replace the canonical continuity algorithm of the sovereign ledger.

**Foundational Axiom (Ω₃):** *Byzantine Default.* The system must operate under the assumption that agents will hallucinate, sub-agents will fail, and input may be adversarial. Verification precedes trust.

---

## 2. The Cryptographic Trust Pipeline

To achieve compliance, an agent memory architecture MUST process all incoming state changes (new memories, updates, deletions) through a strict, unidirectional pipeline before persistence:

1.  **Input Capture**: Raw semantic data is intercepted along with necessary environment metadata (timestamp, model ID, agent intent).
2.  **Epistemic Guard (Validation)**: The input is processed through validation guards to ensure semantic non-contradiction with the existing known state.
3.  **AES-256 Envelope Encryption**: The semantic content and associated metadata are encrypted at rest.
4.  **SHA-256 Ledger Hashing**: The encrypted payload, combined with the hash of the *previous* verified fact, generates a new cryptographic signature, extending the tamper-evident Ledger Chain.
5.  **Vector Embedding (Secondary)**: Only *after* cryptographic validation is the payload embedded for semantic retrieval.
6.  **Storage Engine**: The payload, hash, and vector are committed to the persistence layer.

Failure at any point in this pipeline MUST result in a synchronous `TrustViolationException`. Silent failures or fallback mechanisms are STRICTLY PROHIBITED (See Anti-Pattern AP-1).

---

## 3. The Sovereign Data Schema (The "Fact")

A compliant memory entry is defined as a `Fact`. It represents a tamper-evident unit of recorded state within the system's timeline.

```yaml
required_fields:
  id: "Sequential integer or UUIDv7 (for temporal locality)"
  tenant_id: "String. Supports logical tenant scoping and isolation."
  project: "String. Namespace for the target context."
  fact_type: "Enum: [decision, error, ghost, bridge, discovery, axiom]"
  content: "AES-Encrypted byte array. The recorded semantic payload."
  tags: "Array of Strings."
  confidence: "Enum: [C1, C2, C3, C4, C5]. Epistemic certainty."
  valid_from: "ISO-8601 Timestamp. When the fact became active."
  source: "String. Origin identifier (e.g., agent:gemini_3.1, user:admin)."
  consensus_score: "Float [0.0 - 1.0]. Byzantine consensus weight."
  hash: "String. SHA-256 cryptographic link to prior Fact."

conditional_fields:
  valid_until: "Optional ISO-8601 Timestamp. Marks archival/deprecation."
  tx_id: "Optional Integer. Batched write grouping."
```

---

## 4. Regulatory Alignment: EU AI Act (Article 12)

This protocol is explicitly constructed to support the record-keeping objectives of the **EU AI Act, Article 12** for High-Risk AI Systems. It is a technical substrate for compliance evidence, not a standalone legal guarantee.

| AI Act Requirement (Art. 12) | CORTEX Protocol Implementation |
| :--- | :--- |
| **Automatic recording of events (Logs)** | Recorded interactions are intended to pass through ledger-backed persistence, producing an auditable chronological log of captured system state. |
| **Traceability of AI decisions** | `tx_id` and `causal_edges` preserve provenance links between decisions and previously recorded antecedents when those edges are captured. |
| **Protection against tampering** | The SHA-256 hash chain structure is designed to make retrospective alteration detectable during verification, subject to implementation and key-management assumptions. |

---

## 5. Model Context Protocol (MCP) Integration

The protocol defines standard Model Context Protocol (MCP) tools that conformant servers MUST expose to client LLMs:

-   `cortex_seal`: Commits a verified fact to the Ledger. Requires explicit declaration of `source` and `confidence`.
-   `cortex_verify_chain`: Audits a specific `project` or `tenant_id` to verify the continuity of the hash chain from genesis to the current block under the system's trust assumptions.
-   `cortex_query_provenance`: Returns not just the semantic memory, but its complete lineage, consensus score, and cryptographic signature.

Any memory provider (e.g., Mem0, Zep) integrating the CORTEX Protocol standard must implement these MCP boundaries.

---

## 6. Security & Failure Modes

-   **Hash Collision / Ledger Fork**: If a concurrent write creates a branching ledger, the system MUST pause execution, resolve via consensus score, and explicitly deprecate the orphaned branch via a `ghost` track.
-   **Key Compromise**: The `AES-256` keys are managed by the host OS vault (e.g., `keyring`). If the vault is lost, the semantic content may become operationally irretrievable. The protocol explicitly considers this a feature (crypto-shredding), not a bug.
