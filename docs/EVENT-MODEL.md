# RFC: SORTU-Ω Event Model v0.1
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14

---

## 1. Purpose

This document defines the canonical event model for SORTU-Ω.

The event system exists to expose runtime and coordination truth externally without requiring consumers to inspect internal state stores directly.

It supports:

- real-time integration
- coordination visibility
- audit pipelines
- reactive SDK consumers
- runtime observability

---

## 2. Design Rules

### 2.1 One envelope
All event transports MUST carry the same logical event envelope.

### 2.2 Transport is not semantics
SSE, webhook, and local callback differ in delivery mechanics, not event meaning.

### 2.3 At-least-once beats fantasy
Webhook delivery is at-least-once.
Consumers MUST treat events as potentially replayed.

### 2.4 Event truth is bounded
An event says that the runtime emitted something, not that the entire universe agrees.

---

## 3. Canonical Envelope

```python
from typing import Any, Dict, TypedDict


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

**Required fields**
- `schema_version`
- `event_id`
- `event_type`
- `ts`
- `source`
- `payload`

**Recommended fields**
- `tenant_id`
- `project`
- `sequence`
- `idempotency_key`

---

## 4. Delivery Semantics

### 4.1 Webhooks
- delivery model: at-least-once
- duplicates possible
- consumers SHOULD dedupe by `idempotency_key` and/or `event_id`
- retries SHOULD use stable `idempotency_key`

### 4.2 SSE
- live stream best effort
- not guaranteed replay source unless separately implemented
- `sequence` SHOULD be monotonic where feasible

### 4.3 Local callbacks
- process-local convenience path
- same event semantics
- no new dialects allowed

---

## 5. Canonical Event Types

**Memory**
- `fact.stored`
- `fact.rejected`
- `history.updated`
- `compaction.completed`

**Verification**
- `integrity.failed`
- `verify.completed`
- `taint.escalated`

**Coordination**
- `agent.registered`
- `vote.recorded`
- `consensus.reached`
- `consensus.failed`

**Runtime**
- `runtime.degraded`
- `runtime.recovered`
- `capability.changed`

---

## 6. Payload Guidance

Payloads SHOULD contain:
- stable identifiers
- operation references
- minimal trust-relevant context
- no gratuitous duplication of entire documents or records

**Examples**:
- `fact.stored` → `fact_id`, `operation_id`
- `consensus.reached` → `topic_id`, `quorum_state`, `consensus_id`
- `runtime.degraded` → `components`, `degraded_features`

---

## 7. Ordering and Idempotency

### 7.1 Ordering

Ordering guarantees SHOULD be scoped per source stream, not globally romanticized.

### 7.2 Idempotency

`idempotency_key` SHOULD identify the logical event, not the delivery attempt.

**Bad**:
- new key on each retry

**Good**:
- same key for same logical emission

---

## 8. Event Non-Goals

The event bus is not:
- a full broker abstraction layer
- a Kafka clone
- a guarantee of global total ordering
- a substitute for direct verification APIs

It is a visibility plane.

---

## 9. Final Position

Events should let external systems observe SORTU-Ω without reverse-engineering its organs.

Anything else is decorative telemetry with delusions of grandeur.
