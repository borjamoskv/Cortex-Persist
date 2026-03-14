# RFC: SORTU-Ω Public SDK Surface v0.2
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14
Audience: SDK consumers, platform engineers, compliance integrators, swarm-runtime developers

---

## 1. Purpose

SORTU-Ω provides a **stateful trust layer for agent systems** through typed APIs for:

- **Memory** — persistent storage, retrieval, temporal reconstruction
- **Traceability** — causal lineage and auditability
- **Verification** — guarded execution, integrity checks, trust degradation
- **Coordination** — agent registration, voting, consensus state, event emission
- **Runtime** — health, capability visibility, recovery truth

This RFC defines the **public SDK boundary** for v1.x.

The goal is not to expose internal architecture. The goal is to provide a **clean, stable, inspectable contract** that lets external consumers use the system without understanding its internal retrieval engines, cryptographic structures, or consensus internals.

---

## 2. Design Principles

### 2.1 One intent, one entrypoint
Consumers express **what they want**, not which subsystem they want to fight.

### 2.2 No silent degradation
Important fallbacks MUST become visible in:
- operation results
- query plans
- runtime health
- warnings

### 2.3 Rejection is not failure
The SDK MUST distinguish:
- **success**
- **policy/guard rejection**
- **system/runtime failure**

### 2.4 Runtime is source of truth
Feature availability is determined by `capabilities()` and `health()`, not by docs alone.

### 2.5 Public API hides internal ontology
Terms tied to implementation details SHOULD remain internal unless they create stable, externally observable semantics.

### 2.6 Stability beats cleverness
The surface must be boring enough to survive production.

---

## 3. Stability & Compatibility Contract

The following guarantees apply to all `v1.x` public SDK versions.

### 3.1 Backward compatibility
- New optional fields MAY be added in minor versions.
- Existing published field semantics MUST NOT change within `v1.x`.
- Existing operation names MUST remain stable within `v1.x`.
- Existing event envelope semantics MUST remain stable within `v1.x`.

### 3.2 Error/rejection code stability
- Published rejection and failure codes are stable within `v1.x`.
- New codes MAY be added.
- Existing codes MUST NOT be repurposed.

### 3.3 Capability gating
- Experimental and premium functionality MUST be surfaced through `capabilities()`.
- Consumers MUST NOT infer capability availability from documentation examples.

### 3.4 Deprecation policy
- Deprecated features remain readable before removal where feasible.
- Once a path is marked write-deprecated, no new writes SHOULD be accepted through that path in the next minor that enforces removal.
- Deprecation MUST be surfaced in warnings and/or capability status.

### 3.5 Schema versioning
- Event envelopes MUST contain `schema_version`.
- Export payloads MUST contain `schema_version`.
- Operation metadata SHOULD include schema version when relevant to downstream parsing.

---

## 4. Canonical Domains

The public SDK is grouped into five operational domains:

1. **Memory**
2. **Trace**
3. **Verification**
4. **Coordination**
5. **Runtime**

This grouping is documentary. Consumers may use a flat client if preferred.

---

## 5. Core Types

### 5.1 Evidence

```python
from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict, Union


class EvidenceItem(TypedDict, total=False):
    id: str
    kind: str                  # fact, tx, decision, event, checkpoint, report
    source: str                # ledger, memory, guard, consensus, runtime
    summary: str
    confidence: float
    pointer: str               # stable internal reference or external export pointer
    metadata: Dict[str, Any]
```

---

### 5.2 Query semantics

```python
class QueryFilters(TypedDict, total=False):
    tenant_id: str
    project: str
    fact_types: List[str]
    tags: List[str]
    min_confidence: float
    exclude_tombstoned: bool
    include_quarantined: bool


class QueryInput(TypedDict, total=False):
    query: str
    intent: Literal["lookup", "explore", "audit"]
    strategy: Literal["auto", "text", "vector", "hybrid", "temporal", "graph"]
    filters: QueryFilters
    as_of: str
    top_k: int
    include_graph: bool
    include_history: bool
    include_taint: bool
    include_trace: bool
    explain: bool
```

**Semantics**
- `intent` expresses user purpose.
- `strategy` expresses execution preference.
- `strategy="auto"` delegates routing to the engine.
- `as_of` requests temporal reconstruction or temporal retrieval when applicable.

---

### 5.3 Query plan and evidence level

```python
class QueryPlan(TypedDict, total=False):
    selected_strategy: Literal["text", "vector", "hybrid", "temporal", "graph"]
    fallback_used: bool
    fallback_reason: str
    degraded_mode: bool
    notes: List[str]


class QueryEvidenceLevel(TypedDict):
    level: Literal["none", "basic", "traceable", "verified"]
    reason: str
```

**Evidence levels**
- **none** — raw retrieval, no meaningful provenance
- **basic** — provenance metadata exists
- **traceable** — causal lineage exists
- **verified** — integrity checks completed or linked to verified chain state

---

### 5.4 Query results

```python
class QueryItem(TypedDict, total=False):
    fact_id: str
    content: str
    score: float
    confidence: float
    source: str
    timestamp: str
    evidence_level: QueryEvidenceLevel
    metadata: Dict[str, Any]


class QueryResult(TypedDict, total=False):
    ok: bool
    items: List[QueryItem]
    count: int
    plan: QueryPlan
    warnings: List[str]
    metadata: Dict[str, Any]
```

**Requirements**
- If `strategy="auto"`, `plan.selected_strategy` MUST be present.
- If a meaningful fallback occurs, `plan.fallback_used=True` MUST be set and `fallback_reason` SHOULD be present.
- If the system is degraded in a way that materially affects retrieval quality, `plan.degraded_mode=True` MUST be set.

---

### 5.5 Operation result

```python
class RejectionResult(TypedDict):
    ok: Literal[False]
    kind: Literal["rejection"]
    category: Literal["policy", "safety", "consistency", "integrity", "compliance"]
    code: str
    message: str
    layer: Literal["guard", "membrane", "policy", "verification"]
    rule_id: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence: List[EvidenceItem]
    remediation: List[str]
    metadata: Dict[str, Any]


class FailureResult(TypedDict):
    ok: Literal[False]
    kind: Literal["failure"]
    category: Literal["dependency", "storage", "runtime", "timeout", "capability"]
    code: str
    message: str
    retryable: bool
    component: str
    metadata: Dict[str, Any]


class AcceptanceResult(TypedDict, total=False):
    ok: Literal[True]
    kind: Literal["success"]
    operation_id: str
    warnings: List[str]
    metadata: Dict[str, Any]


OperationResult = Union[AcceptanceResult, RejectionResult, FailureResult]
```

**Semantics**
- **success**: the operation completed
- **rejection**: the system refused the operation by rule or trust policy
- **failure**: the system could not complete the operation due to technical/runtime reasons

---

### 5.6 Health and capabilities

```python
class ComponentHealth(TypedDict, total=False):
    status: Literal["ok", "degraded", "blocked", "disabled"]
    message: str


class HealthReport(TypedDict, total=False):
    status: Literal["ok", "degraded", "blocked"]
    components: Dict[str, ComponentHealth]
    degraded_features: List[str]
    warnings: List[str]
    integrity_ok: bool
    last_integrity_check_at: str


class CapabilityItem(TypedDict, total=False):
    enabled: bool
    tier: Literal["open", "premium", "experimental"]
    status: Literal["ga", "beta", "alpha", "deprecated"]
    reason: str


class CapabilityReport(TypedDict):
    capabilities: Dict[str, CapabilityItem]
```

**Minimum runtime-visible capabilities**
At minimum, `capabilities()` SHOULD report status for:
- `hybrid_query`
- `graph_rag`
- `compaction`
- `wbft_consensus`
- `taint_persistence`
- `compliance_export`
- `working_memory_export`
- `event_bus`

---

### 5.7 Event envelope

```python
class EventEnvelope(TypedDict, total=False):
    schema_version: str
    event_id: str
    event_type: str
    ts: str
    tenant_id: str
    project: str
    source: str
    sequence: int
    idempotency_key: str
    payload: Dict[str, Any]
```

**Delivery semantics**
- Webhook delivery is at-least-once
- SSE delivery is best-effort live stream
- `idempotency_key` SHOULD be stable across redelivery of the same logical event
- `sequence` SHOULD be monotonic per source stream where feasible

---

## 6. Canonical API Surface

---

### 6.1 Memory API

`store(input: StoreInput) -> OperationResult`
Stores a fact, memory item, decision artifact, or related stateful object.

**Expected behavior**:
- passes through guard and/or membrane layers where configured
- writes into storage if accepted
- emits ledger/audit signals where enabled
- returns warnings when operation succeeds under degraded runtime conditions

`query(input: QueryInput) -> QueryResult`
Primary read operation for memory retrieval.

**Expected behavior**:
- routes retrieval according to intent, strategy, runtime availability, and health
- exposes selected plan and fallback behavior
- returns evidence level at item level where possible

`history(input: HistoryInput) -> HistoryResult`
Returns historical evolution of a fact or entity.

`time_travel(input: TimeTravelInput) -> TimeTravelResult`
Returns reconstructed state or retrieval results at a specific past instant.

`compact(input: CompactInput) -> CompactResult`
**Tier**: Premium
Performs memory compaction, clustering, deduplication, or consolidation under configured policy.

`export_working_memory(input?: WorkingMemoryExportInput) -> WorkingMemoryExportResult`
**Status**: Beta / Planned unless fully backed by implementation
Exports session-scoped or working-memory state in a portable representation.

*Public documentation MUST NOT imply deterministic hot failover or full replay guarantees unless explicitly implemented and documented.*

---

### 6.2 Trace API

`trace(input: TraceInput) -> TraceResult`
Returns causal lineage for a target entity.

`TraceInput` SHOULD support one or more of:
- `tx_id`
- `fact_id`
- `decision_id`
- `query_result_id`
- `depth`

*`trace()` is for causality, not primary retrieval.*

`audit(input: AuditInput) -> AuditResult`
Generates an operational trust/audit report.

`export_audit(input: ExportAuditInput) -> ExportAuditResult`
**Tier**: Premium
Exports audit state in canonical JSON, with optional adapters to external formats.

*v1 canonical export SHOULD be stable JSON first. Additional export dialects MAY be layered later.*

---

### 6.3 Verification API

`guard_check(input: GuardCheckInput) -> OperationResult`
Runs a guard/policy check without necessarily performing a write.

`verify(input: VerifyInput) -> VerifyResult`
Verifies integrity and trust state over a requested scope.

Supported verification scopes SHOULD include:
- `fact`
- `project`
- `tenant`
- `time_range`
- `tx_chain`

`VerifyResult` SHOULD indicate:
- verified scope
- number of checked elements
- failures found
- whether legacy verification paths were involved
- whether verification was partial or full

`taint_status(input: TaintStatusInput) -> TaintStatusResult`
Basic current taint visibility MAY exist in open tier.
Persistent taint propagation and policy-driven escalation MAY be premium.

---

### 6.4 Coordination API

`register_agent(input: RegisterAgentInput) -> RegisterAgentResult`
Registers an agent in the coordination layer.

`vote(input: VoteInput) -> OperationResult`
Submits a vote/opinion into the coordination system.

Potential rejection/failure causes include:
- policy block
- stale agent
- insufficient quorum
- capability disabled
- deprecated path usage
- invalid scope

`consensus_status(input: ConsensusStatusInput) -> ConsensusStatusResult`
Returns current consensus state, status, or aggregation result for a task/topic/group.

`publish_event(input: PublishEventInput) -> OperationResult`
Emits a swarm/coordination event into the event system.

*`publish_event` is preferred over vague names like `swarm_event`.*

---

### 6.5 Runtime API

`health() -> HealthReport`
Returns current runtime health.

`capabilities() -> CapabilityReport`
Returns machine-readable capability flags and tiers.

`recovery_status() -> RecoveryReport`
Returns current recovery state, last checkpoint/resume report, or pending recovery warnings where implemented.

`memory_stats() -> MemoryStats`
Returns memory/storage operational metrics.

---

## 7. Query Routing Semantics

### 7.1 Intent

The consumer expresses why they are querying.
- `lookup` — retrieve concrete facts or state
- `explore` — widen search semantically or relationally
- `audit` — prioritize explainability, provenance, and trust evidence

### 7.2 Strategy

The consumer expresses how strictly they want the engine to route.
- `auto` — engine selects best route
- `text` — text-first retrieval
- `vector` — vector-first retrieval
- `hybrid` — hybrid retrieval
- `temporal` — temporal/historical route
- `graph` — graph-enriched route

### 7.3 Required routing behavior

**If strategy != "auto"**
- the engine SHOULD honor the strategy when capability and health allow
- if the strategy is unavailable and fallback is not allowed by contract, return `FailureResult` or equivalent operation failure semantics
- if fallback is allowed, it MUST be visible in `QueryPlan`

**If strategy == "auto"**
the engine MAY select based on:
- `intent`
- `as_of`
- `runtime health`
- `available capabilities`
- `requested evidence level` or `trace inclusion`

### 7.4 Suggested routing policy

**intent="lookup"**
1. temporal if `as_of` is present
2. hybrid if available
3. text fallback

**intent="explore"**
1. graph if available and relevant
2. hybrid
3. vector
4. text fallback

**intent="audit"**
1. temporal and/or hybrid with trace enrichment
2. exclude or downgrade low-provenance results where possible
3. mark degraded mode aggressively if trust signal quality drops

---

## 8. Degraded Mode Semantics

The system MUST NOT silently pretend that degraded results are normal when trust or retrieval quality materially changes.

**Examples of degradation that SHOULD become visible**
- embedder unavailable
- vector search disabled
- graph enrichment unavailable
- ledger verification pending or stale
- taint propagation unavailable
- coordination liveness uncertain
- export adapter unavailable

**Visibility requirements**

Degradation SHOULD be reflected in one or more of:
- `HealthReport.status`
- `HealthReport.degraded_features`
- `AcceptanceResult.warnings`
- `QueryPlan.degraded_mode`
- `QueryPlan.fallback_reason`

---

## 9. Error and Rejection Code Registry

The following registry is canonical for v1.x initial publication.

### 9.1 Rejection codes
- `ERR_CONTRADICTION`
- `ERR_TAINT_HIGH`
- `ERR_POLICY_BLOCK`
- `ERR_COMPLIANCE_SCOPE`
- `ERR_CAPABILITY_DISABLED`
- `ERR_DEPRECATED_WRITE_PATH`
- `ERR_QUORUM_REJECTED`
- `ERR_AGENT_STALE`

### 9.2 Failure codes
- `ERR_EMBEDDER_UNAVAILABLE`
- `ERR_LEDGER_IO`
- `ERR_DB_LOCK_TIMEOUT`
- `ERR_EVENT_DISPATCH_FAILED`
- `ERR_LEGACY_PATH_DISABLED`
- `ERR_COMPONENT_UNAVAILABLE`
- `ERR_RUNTIME_DEGRADED`
- `ERR_VERIFY_SCOPE_INVALID`

*New codes MAY be added in v1.x. Existing codes MUST NOT be repurposed.*

---

## 10. Capability Boundaries

Availability is determined at runtime by `capabilities()`.

### 10.1 Open tier
- storage and persistence core
- text retrieval
- basic hybrid retrieval fallback where enabled
- history / time_travel baseline behavior
- basic guards
- basic ledger/integrity verification
- runtime health and capability visibility

### 10.2 Premium tier
- graph-enriched retrieval
- advanced compaction
- persistent taint propagation
- compliance-grade exports
- advanced immune membrane behavior
- advanced consensus / WBFT / reputation features

### 10.3 Experimental
- not-yet-stable orchestration features
- advanced eventing extensions
- pre-GA working-memory portability features
- formal-methods-adjacent verification features that are not yet fully backed

---

## 11. Deprecation Plan

### 11.1 Memory invalidation semantics

The public contract for tombstone/invalidation semantics MUST converge on a single canonical representation.
- Public-facing invalidation semantics SHALL use `is_tombstoned`
- Legacy internal interpretations such as `valid_until IS NULL` MUST NOT remain externally ambiguous
- Query and dedup behavior MUST align on canonical invalidation semantics

### 11.2 Vote path legacy debt

Legacy vote paths and v2 vote paths are a separate concern from memory invalidation semantics.
- Legacy vote schema MUST be treated as an independent deprecation track
- New writes SHOULD target the canonical vote path only
- Legacy reads MAY remain supported temporarily
- Capability and warnings SHOULD surface deprecation state where relevant

### 11.3 Direct subsystem access

Direct SDK manipulation of internal embedding/vector subsystems SHOULD be deprecated in favor of `store()` and `query()`.

---

## 12. Canonical Events

At minimum, the following event types SHOULD exist where eventing is enabled:
- `agent.registered`
- `vote.recorded`
- `consensus.reached`
- `consensus.failed`
- `fact.stored`
- `fact.rejected`
- `taint.escalated`
- `integrity.failed`
- `compaction.completed`

*All MUST use `EventEnvelope`.*

---

## 13. Example Payloads

### 13.1 Query request

```json
{
  "query": "What did agent alpha conclude about retention decay?",
  "intent": "audit",
  "strategy": "auto",
  "filters": {
    "tenant_id": "tenant_01",
    "project": "cortex-persist",
    "exclude_tombstoned": true,
    "min_confidence": 0.7
  },
  "top_k": 5,
  "include_trace": true,
  "include_taint": true,
  "explain": true
}
```

### 13.2 Query response (degraded fallback)

```json
{
  "ok": true,
  "items": [
    {
      "fact_id": "fact_9a1",
      "content": "Agent alpha concluded retention decay increased after context-window truncation.",
      "score": 0.82,
      "confidence": 0.79,
      "source": "memory",
      "timestamp": "2026-03-14T10:11:00Z",
      "evidence_level": {
        "level": "traceable",
        "reason": "linked causal chain available"
      },
      "metadata": {
        "trace_id": "trace_77d"
      }
    }
  ],
  "count": 1,
  "plan": {
    "selected_strategy": "text",
    "fallback_used": true,
    "fallback_reason": "vector search unavailable: embedder offline",
    "degraded_mode": true,
    "notes": [
      "requested auto strategy",
      "audit intent preserved with text-only provenance"
    ]
  },
  "warnings": [
    "vector_search_unavailable",
    "degraded_mode_active"
  ]
}
```

### 13.3 Rejection result

```json
{
  "ok": false,
  "kind": "rejection",
  "category": "consistency",
  "code": "ERR_CONTRADICTION",
  "message": "Write rejected due to contradiction with existing canonical fact.",
  "layer": "guard",
  "rule_id": "contradiction_guard.v1",
  "severity": "high",
  "evidence": [
    {
      "id": "fact_122",
      "kind": "fact",
      "source": "memory",
      "summary": "Existing fact conflicts with submitted statement.",
      "confidence": 0.94
    }
  ],
  "remediation": [
    "Submit supersession metadata if the new fact is intended to replace the old fact.",
    "Re-run with include_history=true to inspect prior fact evolution."
  ],
  "metadata": {
    "tenant_id": "tenant_01"
  }
}
```

### 13.4 Failure result

```json
{
  "ok": false,
  "kind": "failure",
  "category": "dependency",
  "code": "ERR_EMBEDDER_UNAVAILABLE",
  "message": "Vector retrieval component is unavailable.",
  "retryable": true,
  "component": "embedder",
  "metadata": {
    "degraded_mode": true
  }
}
```

### 13.5 Capability report

```json
{
  "capabilities": {
    "hybrid_query": {
      "enabled": true,
      "tier": "open",
      "status": "ga"
    },
    "graph_rag": {
      "enabled": false,
      "tier": "premium",
      "status": "beta",
      "reason": "license not enabled"
    },
    "wbft_consensus": {
      "enabled": true,
      "tier": "premium",
      "status": "alpha"
    },
    "working_memory_export": {
      "enabled": false,
      "tier": "experimental",
      "status": "beta",
      "reason": "not supported on current runtime"
    }
  }
}
```

### 13.6 Event envelope

```json
{
  "schema_version": "1.0",
  "event_id": "evt_001",
  "event_type": "fact.stored",
  "ts": "2026-03-14T10:33:00Z",
  "tenant_id": "tenant_01",
  "project": "cortex-persist",
  "source": "memory",
  "sequence": 9821,
  "idempotency_key": "fact.stored:tenant_01:fact_9a1",
  "payload": {
    "fact_id": "fact_9a1",
    "operation_id": "op_77aa"
  }
}
```

---

## 14. Non-Goals for v1.x

The following are explicitly out of scope unless separately ratified:
- guaranteed deterministic hot failover from working-memory exports
- full formal proof guarantees from verification terminology alone
- multi-cloud backend abstraction guarantees
- external transport lock-in to Kafka or equivalent heavy brokers
- exposure of raw internal graph, CRDT, or ledger implementation details as public API requirements

---

## 15. Final Position

The public SDK must present SORTU-Ω not as a pile of clever subsystems, but as a trustworthy operational contract.

The engine may remain sophisticated internally.
The surface must remain disciplined externally.

That is the difference between infrastructure that gets admired and infrastructure that gets adopted.
