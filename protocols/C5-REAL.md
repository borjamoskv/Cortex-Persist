# C5-REAL Protocol

## Definition
C5-REAL is an event-sourced sovereignty protocol that models system authority as a replayable, cryptographically verifiable graph. It merges event sourcing, Merkle accumulation, and deterministic replay into a single execution substrate.

---

## Core Model

### 1. Event-Sourced Kernel
All system state is derived from an append-only event log:

```
Event := {
  id: UUID,
  timestamp: int,
  type: string,
  payload: object,
  actor: string,
  parent_hash: string
}
```

State is never mutated directly. It is always reconstructed via replay.

---

### 2. Merkle Authority Layer
Each event is hashed and inserted into a Merkle DAG:

```
H(event) = sha256(canonical(event))
MerkleRoot(t) = aggregate(H(event_0..event_n))
```

Properties:
- Tamper-evident history
- Deterministic state roots per epoch
- Cross-node verifiability

---

### 3. Replayable Authority Graph (RAG)
System authority is expressed as a directed acyclic graph:

```
Node := Agent | System | Contract | Process
Edge := AUTH | REVOKE | DERIVE | OBSERVE
```

Rules:
- AUTH edges grant capability
- REVOKE invalidates downstream authority in replay
- DERIVE creates scoped sub-authorities
- OBSERVE is read-only causality

---

## Execution Semantics

### Deterministic Replay
Given event log E:

```
State_t = reduce(replay(E[0..t]))
```

Any divergence in state implies corruption or fork.

---

## Sovereignty Condition (C5-REAL)
A system is in C5-REAL state if:

1. All state derivation is replayable
2. All authority is traceable in RAG
3. Merkle root is consistent across checkpoints
4. No orphaned authority edges exist
5. Event log is append-only and signed

---

## Failure Modes

- Unsigned event injection → integrity break
- Forked Merkle roots → sovereignty split
- Orphan authority edges → privilege leakage
- Non-deterministic reducers → replay divergence

---

## Minimal Runtime Interface

```
append(event)
replay(from=0, to=latest)
compute_merkle_root(epoch)
verify_authority(node)
```

---

## Extension: Swarm Binding

Each agent in a swarm is a node in RAG:

- Agents inherit capabilities via AUTH edges
- Capability decay is modeled as time-weighted edge attenuation
- Swarm consensus = convergent Merkle root

---

## Cryptographic Hooks

Recommended:
- SHA-256 for event hashing
- Ed25519 for event signing
- Optional: BLS aggregation for swarm signatures

---

## Interpretation
C5-REAL is not a system state.
It is a *constraint on how reality is recorded and replayed.*

If replay fails, reality is invalid.
