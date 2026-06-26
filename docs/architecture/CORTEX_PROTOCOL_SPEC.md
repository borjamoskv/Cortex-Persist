# CORTEX-Persist Protocol Specification (Normative)

**Version:** 1.0.0-draft
**Status:** PROPOSED STANDARD
**Category:** Cryptographic Execution Ledgers

## 1. Introduction

This document specifies the normative architecture of the CORTEX-Persist protocol. It is intended for implementers building CORTEX-compatible nodes in languages other than Python (e.g., Rust, Go, Java) and defines the exact ledger format, cryptographic primitives, and validation invariants required to interoperate within the CORTEX ecosystem.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",  "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

## 2. Cryptographic Primitives

All CORTEX implementations MUST use the following primitives to ensure cross-platform reproducibility of hashes and signatures:

1. **Hashing Algorithm:** `SHA-256` (FIPS 180-4).
2. **Signature Scheme:** `Ed25519` (RFC 8032).
3. **Encoding:** All hashes and public keys MUST be represented as lowercase hexadecimal strings.
4. **Serialization:** All payloads MUST be serialized to Canonical JSON (RFC 8785) before hashing.

## 3. The Ledger Format

The ledger is an append-only, Merkle-linked data structure. Implementations MAY use any storage backend (SQLite, PostgreSQL, LevelDB), provided the logical rows strictly adhere to the following schema.

### 3.1 Logical Row Schema

| Field | Type | Constraint | Description |
|:---|:---|:---|:---|
| `seq_id` | Integer | Monotonically strictly increasing | The sequence index of the block. Starts at 1. |
| `timestamp` | String | ISO 8601 (UTC) | e.g. `2026-06-26T12:00:00.000000Z` |
| `agent_id` | String | UUIDv4 | Identifies the execution entity. |
| `event_type` | String | Max 64 chars | Categorical type (e.g., `observation`, `action`, `inference`). |
| `payload` | String | Valid JSON | The data payload of the event. |
| `prev_hash` | String | 64-char Hex | The `block_hash` of the row where `seq_id = current - 1`. If `seq_id == 1`, this MUST be `0` x 64. |
| `block_hash` | String | 64-char Hex | The cryptographic hash of the current row (see section 3.2). |
| `signature` | String | 128-char Hex | Ed25519 signature of the `block_hash` using the node's private key. |

### 3.2 Block Hashing Algorithm

The `block_hash` MUST be calculated exactly as follows to prevent divergence between implementations:

1. Construct a JSON object mapping the exact keys: `seq_id`, `timestamp`, `agent_id`, `event_type`, `payload`, `prev_hash`.
2. Serialize this object using **Canonical JSON** (no extraneous whitespace, keys sorted lexicographically).
3. Compute the `SHA-256` digest of the UTF-8 encoded canonical byte array.

## 4. Replay Semantics

When replaying a trajectory for deterministic validation, an implementation MUST:
1. Fetch all rows for a given `agent_id`, ordered by `seq_id` ASC.
2. For each row `i` starting from index 0:
   - If `i > 0`, verify `row[i].prev_hash == row[i-1].block_hash`. If false, abort (`MerkleChainMismatchError`).
   - Recompute the `block_hash` using the algorithm in 3.2. If it does not match `row[i].block_hash`, abort (`BlockIntegrityError`).
   - Verify `row[i].signature` using the known public key. If false, abort (`SignatureInvalidError`).

## 5. Invariants (Admission Gates)

A node MUST NOT persist a block if it violates the admission gates. The primary gate is the **Causal Closure Check**:

If `event_type == 'inference'` or `event_type == 'decision'`, the `payload` JSON MUST contain a `causal_graph` object with at least one `evidence_ref` that resolves to a prior `block_hash` in the ledger. 
- *Rationale:* Decisions cannot exist in a vacuum; they must mathematically link to prior evidence in the manifold.

## 6. Audit Pack JSON Standard

To export a verifiable proof, implementations MUST emit an "Audit Pack".

```json
{
  "version": "1.0",
  "public_key": "<ed25519_hex>",
  "chain": [
    {
      "seq_id": 1,
      "block_hash": "...",
      "signature": "...",
      "data": { ... }
    }
  ]
}
```

Any external verifier can independently parse this JSON, sort it, re-hash, and verify the `Ed25519` signatures without needing access to the original database.
