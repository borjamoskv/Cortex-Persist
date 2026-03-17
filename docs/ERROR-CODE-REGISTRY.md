# RFC: SORTU-Ω Error Code Registry v0.1
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14
Audience: SDK consumers, Platform Engineers

---

## 1. Purpose

This registry defines the canonical rejection and failure codes for the SORTU-Ω public SDK.

By separating the error registry from the operational surface, we establish a stable, versionable, and machine-readable contract. This allows downstream consumers (SDKs, UI components, auditors, and compliance handlers) to safely switch on error types without relying on brittle textual matching.

---

## 2. Structural Contract

### 2.1 Rejection vs. Failure

- **Rejections (`kind: "rejection"`)**: Intentional refusals by the system due to governance, policy, taint, or consistency boundaries. The system *could* physically write the data, but *chose* not to.
- **Failures (`kind: "failure"`)**: Unintentional inability to complete an operation due to broken runtime dependencies, IO timeouts, or resource exhaustion. The system *tried* to execute, but *crashed* or *timed out*.

### 2.2 Category Matrix

**Rejection Categories**
- `policy` (Access, Tenant, Auth)
- `safety` (Immune, Chaos, Circuit Breaker)
- `consistency` (Contradiction, DAG Integrity, Logical)
- `integrity` (Hash, Merkle, Ledger Mismatch)
- `compliance` (Regulatory, EU AI Act, Data Residency)

**Failure Categories**
- `dependency` (Embedder, Graph, Search engine)
- `storage` (SQLite, Remote Vector Store)
- `runtime` (Timeout, Concurrency, Event Loop)
- `capability` (Requested strategy unavailable)

---

## 3. Rejection Codes (Governance & Trust Enforcements)

### 3.1 Consistency & Trust
| Code | Category | Severity | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_CONTRADICTION` | `consistency` | `high` | Submitted fact directly contradicts a high-confidence T3 verified fact. | Submit with supersession metadata if intended as an update, or lower the confidence curve. |
| `ERR_TAINT_HIGH` | `consistency` | `critical` | Upstream DAG components have critical taint, making the proposed derivation invalid. | Recompute or execute a trust membrane purification cycle before submission. |
| `ERR_ORPHAN_TRACE` | `consistency` | `medium` | Fact submitted requires causal lineage but parent trace is missing or tombstoned. | Provide valid `trace_id` or parent anchors. |

### 3.2 Integrity & Immutability
| Code | Category | Severity | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_HASH_MISMATCH` | `integrity` | `critical` | Checkpoint or ledger hash fails verification against content payload. | Halt operation. Investigate memory corruption or manual tampering. |
| `ERR_LEDGER_SEALED` | `integrity` | `high` | Attempted to modify or backdate a fact in a sealed ledger block. | Use explicit tombstoning and append new fact. The ledger is immutable. |

### 3.3 Policy & Compliance
| Code | Category | Severity | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_POLICY_BLOCK` | `policy` | `high` | Global or tenant policy explicitly forbids the action (e.g., restricted schema). | Adjust payload to conform to tenant schema constraints. |
| `ERR_COMPLIANCE_SCOPE` | `compliance` | `high` | Data matches PII/Regulatory filters in a non-compliant tenant zone. | Strip PII or route to a compliant vault. |
| `ERR_DEPRECATED_WRITE_PATH` | `policy` | `low` | Using a legacy `valid_until` style write on a v1.x engine that enforces `is_tombstoned`. | Upgrade the SDK payload to use canonical v1.x semantic invalidation. |

### 3.4 Coordination
| Code | Category | Severity | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_AGENT_STALE` | `policy` | `medium` | Vote/Decision submitted by an agent with an expired or missing `liveness` heartbeat. | Re-register agent and restore liveness heartbeat. |
| `ERR_QUORUM_REJECTED` | `consistency`| `high` | Operation requires N-agent quorum, but consensus failed or rejected the proposal. | Review consensus traces. Resubmit to coordination layer. |

---

## 4. Failure Codes (Technical Outages & Degradation)

### 4.1 Dependency & Capability
| Code | Category | Retryable | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_EMBEDDER_UNAVAILABLE` | `dependency` | `True` | The neural embedding service (ONNX/Cloud) is offline. | Switch query strategy to `text` (fallback) or retry with backoff. |
| `ERR_CAPABILITY_DISABLED` | `capability` | `False` | Explicitly requested a premium/experimental feature (e.g., `graph_rag`) that is not licensed or disabled. | Adjust strategy to `auto` or enable capability in system config. |

### 4.2 Storage & IO
| Code | Category | Retryable | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_DB_LOCK_TIMEOUT` | `storage` | `True` | SQLite WAL blocked by heavy concurrent writers. | Implement exponential async backoff. |
| `ERR_LEDGER_IO` | `storage` | `False` | Disk failure or permission denial interacting with `.cortex` underlying memory files. | Check filesystem permissions and space. Severe operational error. |

### 4.3 Runtime
| Code | Category | Retryable | Triggers When | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `ERR_RUNTIME_DEGRADED` | `runtime` | `True` | Operation requested strict execution, but system is under severe thermal/entropic load. | Query `health()` to identify degraded components. |
| `ERR_EVENT_DISPATCH_FAILED` | `runtime` | `True` | Webhook/SSE subsystem blocked or unresponsive during operation emission. | Ensure idempotency keys are steady for async retry via DLQ. |
| `ERR_VERIFY_SCOPE_INVALID` | `runtime` | `False` | Malformed parameters in a formal verification request. | Correct payload schema. |

---

## 5. Extensibility Guarantees

1. The existence of these codes is guaranteed for the `v1.x` lifecycle.
2. Minor versions of the SDK may add new codes. Handlers MUST implement a `default` case to capture unrecognized codes without crashing.
3. If an unrecognized code is encountered, the consumer should lean on the `kind` (`rejection` vs `failure`) to determine if retrying is mathematically sound.

---

## 6. Anti-Patterns

- **String-matching the `message`**: The `message` is for human logs; the `code` is for control flow.
- **Assuming `ok: False` is a bug**: Rejections are successful system enforcements. They are features, not bugs.
- **Retrying Rejections**: Doing an exponential backoff on `ERR_CONTRADICTION` is an entropic waste of compute.
