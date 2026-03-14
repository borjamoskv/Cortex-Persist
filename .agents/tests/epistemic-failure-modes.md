# Cortex-Persist: Epistemic Failure Modes Test Specifications

> **Status:** Draft Test Specs  
> **Parent RFC:** [RFC-CORTEX-NATIVE-AI v0.1](file:///.agents/workflows/RFC-CORTEX-NATIVE-AI.md)  
> **Last Updated:** 2026-03-14

---

## Severity Classification

| Level | Meaning |
| ----- | ------- |
| **S0** | System integrity compromised — data corruption or silent belief falsification |
| **S1** | Consensus integrity compromised — divergent replicas or deadlocked adjudication |
| **S2** | Operational degradation — performance or availability impacted |
| **S3** | Edge case — recoverable anomaly with minor impact |

---

## FM-01: Malicious Veto

- **Severity:** S1
- **Preconditions:** Agent $k$ is a valid swarm participant with non-zero `consensus_weight`.
- **Injection Vector:** Agent submits $p_k(H|E) = 0$ for a belief $H$ that is supported by majority consensus, intending to collapse the LogOP aggregate to zero.
- **Expected System Response:**
  1. Value clamped to $\epsilon_{\min}$ (§3.2 of CRDT Appendix).
  2. `VETO_ATTEMPTED` audit event emitted with agent ID, belief ID, and timestamp.
  3. Aggregate remains non-zero. Collapse requires L3 audit or reinforced quorum.
  4. If repeated ($>3$ vetoes on distinct beliefs within sliding window), agent $k$ is flagged for **Geometric Epistemic Slashing** — exponential reduction of `consensus_weight`.
- **Invariants Verified:** VETO-SAT (no single-agent annihilation), MI-6 (weight adjustments logged).

---

## FM-02: Causal Cycle

- **Severity:** S1
- **Preconditions:** Three or more beliefs exist with cyclic dependency: $A \vdash B, B \vdash C, C \vdash \neg A$.
- **Injection Vector:** Sequential ingestion of beliefs that form a dependency cycle, possibly by different agents unaware of each other's assertions.
- **Expected System Response:**
  1. Cycle detected by ATMS DFS (§5 of ATMS Appendix).
  2. All nodes in cycle transition to CONTESTED.
  3. `CYCLE_DETECTED` event emitted with full cycle path.
  4. Escalation to Epistemic Tribunal for edge severance.
  5. Severed edge becomes a Nogood; backtracking proceeds.
- **Invariants Verified:** No circular reasoning in ACTIVE beliefs; ATMS graph is a DAG for all ACTIVE nodes.

---

## FM-03: Belief Orphaning (Root Revocation)

- **Severity:** S2
- **Preconditions:** Assumption $a$ supports a dependency tree of depth $d \le d_{\max}$ with $|V|$ dependent nodes.
- **Injection Vector:** Assumption $a$ is explicitly revoked via `revise_belief(a, evidence_ref)`.
- **Expected System Response:**
  1. Index lookup: $\text{idx}(a)$ returns all dependent nodes — O(1).
  2. Each dependent node's labels containing $a$ are removed — O(1) per node.
  3. Nodes with empty labels transition to ORPHANED.
  4. Deferred async: system searches for alternative justifications.
  5. Orphaned nodes excluded from Memory Scheduler context immediately.
- **Invariants Verified:** No ORPHANED belief appears in any Context Package; O(1) per-reference invalidation.

---

## FM-04: Source Hash Collision

- **Severity:** S0
- **Preconditions:** Two distinct provenance streams (different `tenant_id` or `signer_id`) produce identical `source_hash` values.
- **Injection Vector:** Intentional hash pre-image attack or accidental collision (probability $2^{-128}$ for SHA-256).
- **Expected System Response:**
  1. SMT insertion detects duplicate leaf with mismatched provenance metadata.
  2. Insertion rejected with `HASH_COLLISION` error.
  3. Incident logged to security audit trail with both provenance envelopes.
  4. If collision is confirmed as attack ($P(\text{accidental}) < 10^{-30}$), source agent is quarantined.
- **Invariants Verified:** SMT leaf uniqueness; provenance binding integrity.

---

## FM-05: Tenant Key Destruction (GDPR Right-to-Erasure)

- **Severity:** S0 (compliance-critical)
- **Preconditions:** Tenant $T$ invokes crypto-shredding via `destroy_tenant_key(T)`.
- **Injection Vector:** GDPR Article 17 request processed.
- **Expected System Response:**
  1. AES-256 master key for tenant $T$ is securely destroyed (zeroized from memory + keyring).
  2. All encrypted payloads (`content`, `meta`) become functionally random ciphertext.
  3. SMT entries for tenant $T$ are marked with destruction tombstones.
  4. ZK proof of unlinking generated: proves key destruction without revealing content.
  5. Cross-tenant references (if any) are severed and logged.
- **Invariants Verified:** No plaintext recoverable post-destruction; ZK proof validates; audit trail complete.

---

## FM-06: Replay Attack on Patches

- **Severity:** S1
- **Preconditions:** Attacker has captured a valid, previously-applied `BeliefPatch` with valid signature.
- **Injection Vector:** Resubmission of the patch after its causal effect has already been absorbed.
- **Expected System Response:**
  1. Patch carries a causal dot $(i, c)$.
  2. Receiving replica checks: $(i, c) \in \text{ctx}(r)$ — already delivered.
  3. Patch is silently discarded (CRDT idempotency).
  4. `REPLAY_DETECTED` audit event emitted if same patch resubmitted $>2$ times.
- **Invariants Verified:** CRDT idempotency; monotonic causal ordering; MI-5.

---

## FM-07: Cascading Orphan Storm

- **Severity:** S2
- **Preconditions:** A foundational assumption $a$ supports $|V| > 10{,}000$ transitive dependents.
- **Injection Vector:** Invalidation of $a$ under high system load (>80% Memory Scheduler utilization).
- **Expected System Response:**
  1. Direct dependents ($|\text{idx}(a)|$) invalidated in O(1) per reference.
  2. Transitive propagation is rate-limited: max $B_{\text{orphan}}$ transitions per tick (default: 500/tick).
  3. Overflow transitions are queued with priority ordering (depth-first from $a$).
  4. Memory Scheduler immediately excludes any node in ORPHANED state from context.
  5. System emits `ORPHAN_STORM` alert if queue depth exceeds $5 \times B_{\text{orphan}}$.
- **Invariants Verified:** System remains responsive under mass invalidation; no ORPHANED belief leaks into context.

---

## FM-08: Sybil Consensus Attack

- **Severity:** S1
- **Preconditions:** Attacker controls $m$ identities in the swarm, each with initial `consensus_weight`.
- **Injection Vector:** All $m$ identities submit identical beliefs designed to inflate LogOP aggregate toward a false conclusion.
- **Expected System Response:**
  1. **Diversity check**: If $>k$ agents submit semantically identical beliefs (cosine similarity > 0.98) within temporal window $\Delta t$, a `CORRELATED_SUBMISSION` alert fires.
  2. **Weight cap**: No single identity cluster (by provenance graph analysis) may hold $> 1/3$ of total `consensus_weight`.
  3. **Proof-of-expertise**: New identities start with minimal weight; weight growth requires demonstrated epistemic accuracy over $>n$ adjudication rounds.
  4. Sybil cluster is flagged for L3 audit.
- **Invariants Verified:** No identity cluster can unilaterally reach quorum; LogOP weight distribution bounded.

---

## FM-09: Stale Tombstone Resurrection

- **Severity:** S3
- **Preconditions:** Tombstone for belief $b$ has been garbage-collected on replica $r_1$ but not yet on replica $r_2$.
- **Injection Vector:** Replica $r_2$ sends a delayed operation referencing belief $b$. Replica $r_1$ has no record of $b$ (neither active nor tombstone).
- **Expected System Response:**
  1. Replica $r_1$ detects an unknown belief reference.
  2. Anti-entropy protocol requests state for $b$ from $r_2$.
  3. If $r_2$ confirms $b$ is tombstoned: $r_1$ creates a synthetic tombstone.
  4. If $r_2$ confirms $b$ is ACTIVE (GC was premature — bug): `PREMATURE_GC` alert fires, $b$ is re-ingested.
- **Invariants Verified:** Causal stability condition for GC (§4.2 of CRDT Appendix); no silent data loss.

---

## FM-10: Split-Brain Merge Conflict

- **Severity:** S1
- **Preconditions:** Network partition divides swarm into partitions $P_1, P_2$. Both partitions independently modify belief $b$'s state.
- **Injection Vector:** $P_1$ transitions $b$ to ACTIVE (via new evidence). $P_2$ transitions $b$ to DISCARDED (via refutation). Partition heals.
- **Expected System Response:**
  1. MV-Register retains both concurrent values: $\{ACTIVE, DISCARDED\}$.
  2. Conflict surfaced to LogOP adjudication with evidence from both partitions.
  3. Until adjudication completes, $b$ is marked CONTESTED.
  4. Memory Scheduler treats CONTESTED beliefs with contamination risk penalty.
  5. Adjudication result is recorded as a signed patch with Nogood if applicable.
- **Invariants Verified:** No silent winner; all concurrent modifications preserved; SEC convergence after adjudication.

---

## FM-11: Temporal Replay with Valid Signature (Monotonic Clock Bypass)

- **Severity:** S0
- **Preconditions:** Attacker has obtained a valid signed patch with dot $(i, c)$ where $c$ is within the current counter range (e.g., by compromising agent $i$'s local state and resetting its counter).
- **Injection Vector:** Submission of a "new" patch with a dot that collides with an existing operation but carries different content.
- **Expected System Response:**
  1. Dot collision detected: $(i, c)$ already exists in causal context with different payload.
  2. `DOT_COLLISION` alert fires — this indicates either a bug or an attack.
  3. Both payloads are preserved in a conflict record.
  4. Agent $i$'s counter is forcibly advanced to $c + \Delta_{\text{safe}}$ (default: 1000).
  5. Agent $i$'s `consensus_weight` is reduced pending L3 investigation.
  6. If confirmed attack: agent $i$ quarantined; all patches from $i$ since compromise reviewed.
- **Invariants Verified:** Monotonic counter integrity; no silent overwrite; attack surface bounded.
