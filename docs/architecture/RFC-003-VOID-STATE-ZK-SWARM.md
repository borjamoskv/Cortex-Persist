# RFC 003: Void-State Security Architecture & ZK-Swarm Consensus

## Abstract
This document introduces the **Void-State Security Architecture**, an operating paradigm that moves the CORTEX multi-agent ecosystem away from soft "rules" and "guardrails" towards rigorous **cryptographic execution proofs** (ZK-Swarm consensus). The overarching objective is to resolve the Epistemic Containment Problem natively: mitigating LLM hallucinations and drift not through prompt engineering, but through Byzantine-resilient verification and zero-knowledge evidence anchored to an immutable ledger.

## 1. El Teorema de la Contención Epistémica (Epistemic Containment Theorem)

At `Legion-100` and eventually `Legion-10000` scale, inference entropy (hallucination, drift, instruction-forgetting) is no longer an anomaly—it is background radiation.

**Postulate:** Purely linguistic constraints (prompts, constitutional AI, soft guardrails) form a permeable membrane. Under sustained thermodynamic friction, any LLM layer will eventually leak entropy.
**Corollary:** The only acceptable containment boundary in a "Void-State" environment is hard cryptographic verification. The cost of generating a false trajectory must become mathematically or algorithmically prohibitive. 

If a subagent hallucinates a module change or a tensor shift, it must be discarded *before* it propagates to the CORTEX memory ledger.

## 2. ZK-Swarm Consensus: Byzantine Tolerance over LLM Inference

In distributed systems, Byzantine Fault Tolerance (BFT) ensures consensus despite malicious or faulty nodes. In the CORTEX protocol, "faulty nodes" translate directly to "hallucinating subagents." 

### The Mechanism
Instead of trusting a single inference run to generate a deterministic truth:
1. **Parallel Execution (Quorum):** Let `N` subagents (where `N >= 3`) receive the exact same context hash.
2. **Stochastic Divergence Filtering:** Each agent reasons independently. Their reasoning traces are stochastically divergent, but the proposed **execution delta** (the state change) must be homologous.
3. **ZK-Proof Generation:** Instead of flooding the memory bus with the entire reasoning chain, the agent generates a Zero-Knowledge Proof (e.g., a lightweight SNARK/STARK) over the *execution path* that led to this delta. 
4. **Validation:** The network validates the proof in `O(1)` time relative to the `O(P)` inference time. 

### Consensus Threshold
A state change is only valid if a supermajority agrees on the exact cryptographic hash of the resulting execution delta:
`Quorum = floor((2N + 1) / 3)`

## 3. Void-State Transition Cycle

The traditional pipeline relies on: `Prompt -> Inference -> Write to DB`.
The new **Void-State Transition Cycle** operates under 4 atomic phases:

1. **Plasma (Inference):** The raw generation phase where the LLM produces a solution. This state is mathematically undefined and untrusted. Maximum entropy.
2. **Colapso (ZK Projection):** The node distills its reasoning into a deterministically reproducible script or structured data delta, signing it with its local `Ed25519` key and attaching a succinct execution proof.
3. **Cristalización (Consensus):** Sibling shards (or a localized orchestrator running DVT-style validation) receive the signature and proof. The execution is validated without needing to parse the semantic "noise" that led to it.
4. **Void-State (Anchoring):** Only valid, quorum-approved state deltas are appended to `cortex.db` and anchored securely to the local Git DAG.

## 4. The Thermodynamics of Byzantine Consensus

In CORTEX Axioms (Ω₂), exergy is the supreme currency. 
Why spend additional tokens or compute cycles to generate ZK proofs and run parallel quorums?

**The Blast Radius Equation:**
It is thermodynamically cheaper to spend `Ep` (exergy of generating a proof) than to spend `Er` (exergy of rolling back a catastrophic failure in production).
If `Ep < (Er * Pfailure)` then the action is thermodynamically positive.

A `Pfailure` in a 10,000-agent swarm approaches `1.0` continuously. Therefore, ZK-Swarm consensus is not just a security measure; it is a **thermodynamic necessity** to prevent cascading systemic collapse.

## 5. CORTEX-Native Implementation Blueprint

To materialize this theory into the existing `Cortex-Persist` ecosystem, the following phased architectural adjustments are mapped:

### Phase 1: Local Multi-Process Consensus (The Seed)
- Introduce `ZKGuardMixin` to the engine layer to enforce mathematical checks before state changes.
- Enforce local `Ed25519` keypair generation for each `SwarmRunner` process.
- Subagents output deterministic structural patches (e.g., generic AST diffs, PeARL symbolic logic) instead of semantic markdown, and sign them. 
- The `ForensicCommander` verifying operations acts as the initial central verifier, treating the signatures mathematically.

### Phase 2: Distributed Ledger Alignment (DVT Parity)
- Move to an architecture fundamentally inspired by Ethereum's SSV (Secret Shared Validators).
- Expose the CORTEX Event Bus as a verifiable P2P substrate.
- Shard validation tasks across multiple virtual nodes. 
- Operations mutating `cortex.db` require a threshold of `k-of-n` cryptographic signatures from the decentralized local network. 

---
> *Nueve leyes. La última es el fin del software.*
> *Compresión Shannon v6.0 — CORTEX Unified Substrate.*
