# CORTEX-Persist Formal Model

> *"An agent's execution history is not a log — it is a point in a high-dimensional metric space."*

This document defines the formal mathematical invariants that CORTEX-Persist guarantees. It bridges the gap between software engineering and verifiable evidence, providing the rigorous foundation required for CTOs and auditors to trust the system.

## 1. The State Transition Pipeline

The core mechanism of CORTEX is a strictly unidirectional transformation from stochastic probability to deterministic cryptographic proof:

```text
Stochastic_State (LLM)
       ↓
[ Admission Gates ]
       ↓
Validated_Decision
       ↓
[ Canonical JSON Serialization ]
       ↓
Payload_Hash (SHA-256)
       ↓
[ Merkle Chaining: Hash(Prev_Hash + Payload_Hash) ]
       ↓
Block_Hash
       ↓
[ Ed25519 Signing ]
       ↓
ZK_Seal (Signature)
       ↓
[ Append to SQLite / AOF Binary ]
       ↓
Immutable_Ledger_Row
       ↓
[ JSON Export ]
       ↓
Verifiable_Audit_Pack
```

## 2. Axiomatic Guarantees

CORTEX operates under the following formal invariants:

### Axiom 1: Causality (No Magic Leaps)
Let $E$ be an event proposed by an agent. $E$ is only persisted if there exists a directed path in the Causal Graph from known evidence $V$ to $E$.
$$ \forall E \in Ledger, \exists V \in Ledger : V \rightarrow E $$
*Implementation:* `CausalClosureGuard` rejects isolated conclusions.

### Axiom 2: Cryptographic Continuity (Append-Only)
Let $B_n$ be the $n$-th block in the ledger. Its hash $H_n$ is a strict function of its contents $C_n$ and the previous hash $H_{n-1}$.
$$ H_n = \text{SHA256}(C_n \parallel H_{n-1}) $$
*Implementation:* `MerkleChainMismatchError` triggers on any divergence.

### Axiom 3: Sovereign Authenticity
Let $S_n$ be the signature of block $n$. It must be verifiable by the public key $K_{pub}$ of the sovereign node that executed it.
$$ \text{Verify}(K_{pub}, H_n, S_n) = \text{True} $$
*Implementation:* `Ed25519SignatureInvalid` aborts the replay or verification process.

### Axiom 4: Thermodynamic Bounding (Exergy)
Let $\Delta S$ be the structural mutation induced by an event, and $E_{max}$ be the maximum allowed energy (exergy budget) per tick.
$$ \Delta S \le E_{max} $$
*Implementation:* `EntropyDriftThresholdExceeded` triggers if an agent loops or hallucinates uncontrollably.

## 3. The Verification Replay

To independently verify an Audit Pack, any external script (even one not using CORTEX) can perform the following $O(N)$ deterministic replay:

```python
def verify_audit_pack(pack: list, public_key: bytes) -> bool:
    prev_hash = "0" * 64
    for block in sorted(pack, key=lambda x: x.seq_id):
        # 1. Recompute Payload Hash
        payload_hash = sha256(canonical_json(block.data))
        
        # 2. Recompute Block Hash
        expected_hash = sha256(payload_hash + prev_hash)
        if block.block_hash != expected_hash:
            return False # Chain broken
            
        # 3. Verify Signature
        if not ed25519_verify(public_key, expected_hash, block.signature):
            return False # Forged block
            
        prev_hash = expected_hash
        
    return True
```

Because this algorithm is deterministic and relies on standard cryptographic primitives (SHA-256, Ed25519), CORTEX execution lineage is universally verifiable.
