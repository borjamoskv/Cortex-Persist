# Anatomy of a CORTEX Audit Pack

When operating autonomous AI systems in high-risk or regulated environments, stating "the agent decided to do X" is insufficient. You need an exportable, mathematically defensible proof. CORTEX generates **Audit Packs**—zero-trust, cryptographically sealed JSON files that provide an irrefutable trail of events.

> **View Live Artifact:** `examples/audit_proof_artifact.json`

---

## 1. The Core Payload (What happened)

Every record securely binds context to an explicitly defined agent, tenant, and timestamp.

```json
  "audit_receipt": {
    "tenant_id": "customer-123",
    "project": "fin-fraud-bot",
    "agent_id": "risk-bot",
    "fact_id": "fact_01JMWP2K9ZXG7VQY8A1S3RT5D",
    "fact_type": "decision",
    "content": "Transaction flagged: IP mismatch...",
    "timestamp": "2026-03-31T18:42:01.192Z"
  }
```

* **Why it matters:** In traditional logs, this metadata is easily overwritten by a database admin or lost during a log rotation. When stored in CORTEX, this specific payload is mathematically locked.

## 2. The Cryptographic Proof (Why it matters)

The exact payload from Step 1 is hashed, and that hash is chained to the *previous* state of the memory system, creating a blockchain-like immutable ledger inside your private SQLite Database.

```json
  "cryptographic_proof": {
    "ledger_index": 142095,
    "previous_hash": "e3b0c44298...",
    "current_hash": "8f4a2b9e61...",
    "merkle_root_sealed": true,
    "proof_of_work_nonce": 98412,
    "tamper_detected": false,
    "signature": "sig_0x42f7c0a..."
  }
```

* **`previous_hash` & `current_hash`:** Prevent the insertion, deletion, or reordering of historical records.
* **`merkle_root_sealed`:** Proves the local block connects to the global, signed snapshot of your organization's total memory.
* **`tamper_detected`:** If *anyone* (an attacker, an admin, or an LLM) edits the row directly using raw SQL, this boolean will automatically flip to `true` upon the next verification read, emitting an alert system-wide.

## 3. The Verification Command (How to test it)

The audit pack provides the exact CLI instruction required for an external auditor, compliance officer, or legal team to verify the data against the live database without writing code.

```json
  "verification_command": "cortex verify 142095"
```

* **Why it matters:** Real compliance requires reproducibility. Any stakeholder can run a fact-level
  verification command like this, or the broader `cortex trust-ledger verify`, to mathematically
  guarantee ledger integrity.

## Conclusion

Standard vector stores (Pinecone, Milvus, Qdrant) give you similarities.
Standard logging platforms (Datadog, Elastic) give you timestamps.

**CORTEX Persist gives you the mathematically proven Cognitive Lineage.**
