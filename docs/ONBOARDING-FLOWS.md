# RFC: SORTU-Ω Onboarding Flows v0.1
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14
Audience: New Integrators, Swarm Developers, Platform Architects

---

## 1. Purpose

This document provides definitive **Onboarding Flows** for engineers adopting the SORTU-Ω public SDK. 

Instead of reading raw endpoint documentation in isolation, integrators should start here to understand the four primary operational loops:

1. **Working Memory Integration** (The RAG / Persistence Loop)
2. **Audit & Trace Integration** (The Compliance Loop)
3. **Verification Integration** (The Integrity Loop)
4. **Coordination Integration** (The Swarm Loop)

For each flow, we define the **happy path**, the **degraded path**, and the **rejection path**.

---

## 2. Working Memory Integration (The RAG Loop)

This is the most common integration: storing facts and retrieving them for generation.

### 2.1 The Write Path
**Goal:** Persist an observation or decision.

1. **Client** calls `sdk.memory.store(fact)`.
2. **SORTU-Ω** runs policy guards, contradiction checks, and taint evaluation.
   - **Happy Path:** Returns `AcceptanceResult`. The fact is durably stored and indexed.
   - **Rejection Path:** Returns `RejectionResult` (e.g., `ERR_CONTRADICTION`). The client MUST NOT retry; it must resolve the semantic conflict (e.g., submit with supersession metadata).
   - **Failure Path:** Returns `FailureResult` (e.g., `ERR_EMBEDDER_UNAVAILABLE`). The client MAY retry if the error is marked `retryable`.

### 2.2 The Retrieval Path
**Goal:** Retrieve facts to build context for an LLM.

1. **Client** calls `sdk.memory.query(intent="lookup", strategy="auto")`.
2. **SORTU-Ω** determines the optimal execution plan.
   - **Happy Path:** Returns `QueryResult` with vector-enriched, temporally accurate items. `plan.fallback_used` is `false`.
   - **Degraded Path:** Returns `QueryResult` but `plan.degraded_mode` is `true` (e.g., vector search failed, fell back to basic text retrieval). 
   - *Integration Rule:* If `degraded_mode` is true, the client SHOULD warn the user or lower the temperature of the subsequent LLM generation, as the context density is compromised.

---

## 3. Audit & Trace Integration (The Compliance Loop)

This flow is used by compliance officers, red teams, or debugging agents to understand *why* the system believes something.

### 3.1 The Provenance Path
**Goal:** Trace a fact back to its origin.

1. **Client** calls `sdk.trace.trace(fact_id="fact_123")`.
2. **SORTU-Ω** traverses the causal DAG backward.
   - **Happy Path:** Returns a `TraceResult` graph from the target fact down to the root axioms or external sensor inputs.
   - **Rejection Path:** Returns `RejectionResult` (e.g., `ERR_COMPLIANCE_SCOPE` if the trace crosses into a tenant boundary the client cannot read).

### 3.2 The Trust Audit Path
**Goal:** Prove the system's operational integrity at a specific point in time.

1. **Client** calls `sdk.trace.audit(intent="audit")`.
2. **SORTU-Ω** generates a trust report.
   - *Integration Rule:* The client SHOULD inspect the `evidence_levels` in the returned report. If the majority of facts are listed as `none` or `basic`, the audit fails the "High Trust" internal bar. The client requires `traceable` or `verified` evidence.

---

## 4. Verification Integration (The Integrity Loop)

This flow is used to ensure the memory hasn't been tampered with or silently corrupted.

### 4.1 The Snapshot Check
**Goal:** Validate that a specific project's state is cryptographically sound.

1. **Client** calls `sdk.verification.verify(scope="project", project_id="alpha")`.
2. **SORTU-Ω** recalculates the Merkle roots and cross-references the Master Ledger.
   - **Happy Path:** Returns `VerifyResult` with status `verified`. The client can proceed with high-stakes autonomous execution.
   - **Failed Path:** Returns status `failed`. 
   - *Integration Rule:* If `failed`, the client MUST immediately halt autonomous execution for that project and alert a human operator or the Immune System daemon.

### 4.2 The Taint Check
**Goal:** Ensure a workflow isn't using contaminated data.

1. **Client** calls `sdk.verification.taint_status(fact_id="fact_123")`.
2. **SORTU-Ω** calculates the propagation of downstream risk.
   - *Integration Rule:* If status is `high` or `medium`, the client SHOULD refuse to use the fact in a critical path (e.g., financial transactions, physical actuation) without explicit human override.

---

## 5. Coordination Integration (The Swarm Loop)

This flow is used by multi-agent swarms to vote, reach consensus, and share state.

### 5.1 The Registration Path
**Goal:** An agent joins the swarm and announces its capabilities.

1. **Client (Agent A)** calls `sdk.coordination.register_agent()`.
2. **SORTU-Ω** active agents broadcast a `agent.registered` event.

### 5.2 The Consensus Path
**Goal:** Multiple agents vote on a decision (e.g., "Is this PR safe to deploy?").

1. **Clients (Agents A, B, C)** call `sdk.coordination.vote(topic_id="deploy_42", decision="approve")`.
2. **SORTU-Ω** aggregates votes against quorum rules.
   - **Happy Path:** Quorum reached. The system emits a `consensus.reached` event via Webhooks/SSE.
   - **Rejection Path:** Returns `ERR_AGENT_STALE` for Agent C. 
   - *Integration Rule:* The swarm orchestration layer MUST listen for `consensus.failed` or `consensus.reached` events via the Event Bus, rather than polling the database.

---

## 6. Real-World Anti-Patterns to Avoid

- **Ignoring `plan.degraded_mode` in QueryResults.** (Result: AI generates garbage because it silently fell back to a poor retrieval strategy).
- **Treating Rejections as Exceptions.** (Result: Infinite retry loops hammering the database because a fact contradicted a policy).
- **Relying on Polling for Consensus.** (Result: Deadlocks and timeouts. Use the `EventEnvelope` streams).
- **Using `intent="explore"` for Compliance Audits.** (Result: The system returns broad semantic matches with poor `evidence_level` scores, failing the audit).
