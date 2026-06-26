# CORTEX-Persist Formal Model

The execution history of an agent is not a log file.
It is an append-only, cryptographically verifiable sequence of state transitions.

## 1. State Transition Pipeline

Let:
- \( S_t \) be the stochastic proposal emitted by the agent at time \( t \).
- \( G(S_t) \) be the admission gate function.
- \( D_t \) be the validated decision after policy evaluation.
- \( M_t \) be the metadata vector (including `seq_id`, `timestamp`, `node_id`, `schema_version`, and `policy_id`).
- \( J(\cdot) \) be the canonical JSON serialization.
- \( P_t = \text{SHA-256}(J(D_t)) \) be the payload hash.
- \( H_t = \text{SHA-256}(H_{t-1} \parallel P_t \parallel J(M_t)) \) be the block hash.
- \( \sigma_t = \text{Ed25519\_Sign}(sk, H_t) \) be the block signature (Auth-Seal).
- \( R_t = (seq\_id, H_t, \sigma_t, D_t, M_t) \) be the immutable ledger row.

The exported audit pack is the ordered sequence:
\( A = [R_1, R_2, \dots, R_n] \)

## 2. Invariants (Axiomatic Guarantees)

### Axiom 1 — Causal Admissibility
An event \( E \) is persisted only if it is derivable from an admissible evidence set \( V \) under the system policy \( \Pi \):
\[ V \vdash_{\Pi} E \]

### Axiom 2 — Append-Only Continuity
For every block \( R_t \):
\[ H_t = \text{SHA-256}(H_{t-1} \parallel P_t \parallel J(M_t)) \]
Any mutation of historical content mathematically invalidates the chain.

### Axiom 3 — Signature Authenticity
For every block \( R_t \):
\[ \text{Verify}(pk, H_t, \sigma_t) = \text{True} \]
If verification fails, the block and all subsequent derivations are rejected.

### Axiom 4 — Bounded Structural Drift
Let \( d(S_{t-1}, S_t) \) be a system-defined metric over state transitions.
Then:
\[ d(S_{t-1}, S_t) \le \epsilon \]
where \( \epsilon \) is the maximum permitted drift (exergy budget) per tick.

## 3. Definitions

- **canonical_json (\( J \))**: A strict byte-level serialization of a JSON object mapping (RFC 8785). No extraneous whitespace, keys sorted lexicographically, encoded in UTF-8.
- **policy (\( \Pi \))**: The sum of all active `Guards` (e.g., Contradiction, Exergy, Dependency) that determine if a state transition is allowed.
- **admissible evidence (\( V \))**: A set of block hashes previously committed to the ledger that the agent cites to justify its current decision.
- **state metric (\( d \))**: The geometric distance function mapping two execution vectors in the execution manifold. Used to calculate Entropy Drift.
- **metadata vector (\( M_t \))**: Contains the environmental and topological facts of the execution: `seq_id`, ISO `timestamp`, `node_id`, `schema_version`, and `policy_id`.
- **fork resolution**: In the event two proposals derive from \( H_{t-1} \), the `MetaArbiter` performs a topological collapse selecting the branch with the lowest \( d \). The other is marked divergent.
- **tamper response**: Any verification failure results in an immediate `SAGA-Abort` or process `SIGKILL`.

## 4. Deterministic Verification

This \( O(N) \) algorithm independently verifies an Audit Pack. The input `pack` MUST be pre-ordered by `seq_id`.

```python
import hashlib
import ed25519  # abstract standard lib

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def canonical_json(data: dict) -> bytes:
    import json
    return json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')

def verify_audit_pack(pack: list, public_key: bytes) -> bool:
    # pack must already be ordered by seq_id
    prev_hash = b"\x00" * 32

    for block in pack:
        payload_hash = sha256(canonical_json(block.data))
        metadata_bytes = canonical_json(block.meta)

        # Exact concatenation order
        expected_hash = sha256(prev_hash + payload_hash + metadata_bytes)

        if bytes.fromhex(block.block_hash) != expected_hash:
            return False # Chain continuity broken

        if not ed25519.verify(public_key, expected_hash, bytes.fromhex(block.signature)):
            return False # Auth-Seal invalid

        prev_hash = expected_hash

    return True
```
