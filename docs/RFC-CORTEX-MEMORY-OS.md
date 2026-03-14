# RFC: CORTEX Memory OS (Axiom Ω₁₃ Enforcement)

**Status:** Draft / Active
**Date:** March 2026
**Target Architecture:** MOSKV-1 v5 / CORTEX v8

## 1. Context and Motivation

Currently, CORTEX memory operations lack explicit thermodynamic separation between working context and persistent state, operating closer to a flat vector store. To achieve truly scalable, long-horizon autonomous agents without context collapse or excessive token consumption (Entropic Decay), we must transition memory from a mere "store" to a true **Cognitive Operating System**. 

This redesign integrates the architectural principles of three specialized systems, strictly filtered through **Axiom Ω₁₃ (Termodinámica Cognitiva)**:
- **Mem0:** For the physics of tokens (cost/latency extraction pipelining).
- **Memory OS:** For systemic governance (policy-governed memory classes).
- **HiAgent:** For forced context collapse and subgoal compression in long-horizon tasks.

---

## 2. Axiomatic Enforcement (Ω₁₃)

Any new memory module must satisfy the following constraints:
1. **Cost of Order:** Every memory mutation (store, search, compound) costs energy. `shannon/exergy.py` applies.
2. **Maxwell's Demon (Admission Guard):** Fact insertion requires an explicit `extract -> consolidate -> store` pipeline. No fact is persisted without passing the exergy threshold.
3. **Ghost Annihilation:** Action-observation traces must be compressed and deleted after the goal is achieved to prevent carrying semantic radiation into new cycles.

---

## 3. Topología de Subsistemas

The Memory OS is composed of four heavily isolated modules:

### 3.1. `cortex/compaction/mem0_pipeline.py` (The Thermodynamic Filter)
Responsible for preventing unverified, low-exergy conversational data from entering the CORTEX Ledger. 
- **Extract:** Parses entities, intent, and relationships from the episodic context.
- **Consolidate:** Resolves collisions, contradictions, and redundancy (compresses `H(X)`).
- **Store:** Commits to the `ledger.py` explicitly as semantic/persistent memory.
- **Impact:** Expected 90% reduction in token retrieval overhead (Mem0 baseline).

### 3.2. `cortex/policy/memory_os.py` (The OS Hypervisor)
Enforces access and mutation policies across distinct memory domains.
- **Clases:** `[Working]`, `[Episodic]`, `[Semantic]`
- Agents do not run a "global search". The `MemoryOS` daemon routes exact requests to the required tier, metering token budgets.

### 3.3. `cortex/context/hiagent.py` (Subgoal Compression)
Prevents attention collapse during long-horizon loops (e.g., NightShift).
- Aggregates action-observation loops during a given step.
- Once the step succeeds, it forces **Amnesia Local**: compressing the trace into a single derivative crystal and flushing the raw trace.
- Leaves zero "code ghosts" behind.

### 3.4. `cortex/engine/` (Routing Integration)
Coordinates the RAG bypass. Replaces standard vector search with a targeted causal query (`causal_gap_reduction`) through the Memory OS.

---

## 4. Execution Plan (Code Scaffolding)

1. Scaffolding of the OS classes in `cortex/policy/`.
2. Implementation of the `mem0_pipeline` (Extract -> Consolidate -> Store) with Exergy Guard.
3. Implementation of the `hiagent` context manager (Subgoal compression).
4. Unification via the `cortex.engine` RAG interface.

## 5. Security & Trust Impact
Continues strictly relying on `ledger.py` for immutable writes. The new admission pipeline serves as a pre-ledger Guard, enhancing the verification described in `SECURITY_TRUST_MODEL.md`. No changes permitted to core crypto boundaries.
