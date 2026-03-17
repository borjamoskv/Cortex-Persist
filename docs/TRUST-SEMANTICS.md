# RFC: SORTU-Ω Trust Semantics v0.1
Status: Draft
Program: ORTU-Ω Forge
Codename: SORTU-Ω
Last Updated: 2026-03-14
Audience: SDK consumers, platform engineers, compliance integrators, runtime maintainers

---

## 1. Purpose

This document defines the **trust semantics** that govern SORTU-Ω public behavior.

`SDK-SURFACE.md` defines the shape of the API.
This document defines the meaning of its outputs.

It specifies:

- evidence levels
- degraded mode semantics
- rejection vs failure semantics
- integrity semantics
- taint semantics
- trust expectations for retrieval, write, verification, and coordination flows

The goal is simple:

> the system must not merely produce results; it must make their trust posture legible.

---

## 2. Trust Model

SORTU-Ω is not a generic retrieval engine.
It is a **stateful trust layer**.

Trust is represented through composition of:

1. **provenance** — where a result came from
2. **causality** — how it came to exist
3. **integrity** — whether its surrounding chain is structurally valid
4. **policy posture** — whether it passed applicable rules
5. **taint posture** — whether error or contamination risk has propagated into it
6. **runtime posture** — whether the system is operating in normal or degraded conditions

Trust is never binary in the public surface.
It is exposed as a set of machine-readable signals.

---

## 3. Foundational Principles

### 3.1 No false confidence
The system MUST NOT present degraded, weakly sourced, or weakly verified results as if they were equivalent to fully traceable or verified results.

### 3.2 Silence is not neutrality
If important retrieval, policy, or verification signals are missing, that absence SHOULD be surfaced as reduced trust, not hidden as normalcy.

### 3.3 Rejection is informative
A rejected operation is still a successful act of governance if the rejection is intentional, explainable, and machine-readable.

### 3.4 Failure is operational, not moral
A component outage or dependency failure is not a policy decision. It MUST be represented as a technical failure, not disguised as rejection.

### 3.5 Evidence is cumulative
Trust increases when multiple dimensions align:
- provenance exists
- lineage exists
- integrity holds
- taint is absent or low
- runtime is healthy

### 3.6 Degradation must be visible
If runtime degradation materially changes retrieval quality, verification power, or governance enforcement, public outputs MUST reflect it.

---

## 4. Trust Dimensions

### 4.1 Provenance
Provenance answers:
- where did this item come from?
- what subsystem produced or stored it?
- what identifiers anchor it?

Minimum provenance may include:
- source subsystem
- fact/tx/decision identifier
- timestamp
- tenant/project scope

### 4.2 Causality
Causality answers:
- what prior decision, write, or event led to this item?
- what parent or predecessor relationship exists?
- can lineage be traversed?

### 4.3 Integrity
Integrity answers:
- is the relevant chain structurally intact?
- does the system have evidence that ledger/hash/Merkle checks passed?
- was verification full, partial, or unavailable?

### 4.4 Policy posture
Policy posture answers:
- was the operation or item accepted under current rules?
- was it blocked, quarantined, downgraded, or passed?

### 4.5 Taint posture
Taint posture answers:
- is the item downstream from known contradictions, failures, or suspect parents?
- has trust been downgraded through propagation?

### 4.6 Runtime posture
Runtime posture answers:
- was the system healthy when the operation occurred?
- were required capabilities available?
- were important fallbacks triggered?

---

## 5. Evidence Levels

Evidence levels communicate the minimum trust visibility attached to a result.

### 5.1 Canonical levels

```python
from typing import Literal, TypedDict


class QueryEvidenceLevel(TypedDict):
    level: Literal["none", "basic", "traceable", "verified"]
    reason: str
```

### 5.2 Semantics

**none**
The result exists, but the public surface cannot attach meaningful provenance or trust evidence.

Typical cases:
- raw text match
- minimal metadata
- transient or weakly anchored retrieval
- degraded subsystem with no lineage available

*This level SHOULD be treated as informational, not strongly trusted.*

**basic**
The result has basic provenance and metadata but no strong causal chain.

Typical cases:
- source and timestamp known
- stable fact ID exists
- no trace expansion requested or available
- integrity state not attached

*This level is usable for general retrieval but weak for audit or compliance workflows.*

**traceable**
The result can be linked to causal lineage.

Typical cases:
- causal chain exists
- trace ID or parent decision link exists
- provenance is stable enough to follow backward

*This is the minimum serious level for trust-centric workflows.*

**verified**
The result is linked to or embedded in verified integrity state.

Typical cases:
- ledger/hash/Merkle checks passed
- verification completed recently enough to be relevant
- chain state is structurally valid
- evidence is not merely present, but structurally checked

*This is the strongest public trust level.*

### 5.3 Rules
- Systems MUST NOT emit `verified` without actual integrity basis.
- Systems SHOULD NOT emit `traceable` if no meaningful lineage can be traversed.
- Systems MAY downgrade a result’s evidence level under degraded mode.
- `intent="audit"` SHOULD preferentially return `traceable` or `verified` items where possible.

---

## 6. Trust Grades (Optional Aggregate View)

Some consumers may want a higher-level summary beyond evidence levels.

A runtime MAY expose an aggregate trust grade:

```python
from typing import Literal, TypedDict


class TrustGrade(TypedDict):
    grade: Literal["T0", "T1", "T2", "T3"]
    reason: str
```

**Suggested interpretation**
- T0 — low trust / informational only
- T1 — provenance known
- T2 — causally traceable
- T3 — integrity-backed / verified

*This is optional and MUST NOT replace the underlying explicit signals.*

---

## 7. Degraded Mode Semantics

Degraded mode is a first-class trust signal, not a hidden implementation detail.

### 7.1 Definition

A system is in degraded mode when one or more unavailable, stale, or impaired components materially affects:
- retrieval quality
- verification power
- policy enforcement
- coordination confidence
- export fidelity

### 7.2 Examples

The following SHOULD trigger visible degradation signals when materially relevant:
- embedder unavailable
- vector retrieval disabled
- graph enrichment unavailable
- ledger verification stale or pending
- taint propagation unavailable
- event bus unavailable where required for coordination visibility
- agent liveness unknown
- export adapter unavailable
- memory portability/export unavailable when explicitly requested

### 7.3 Visibility requirements

Degraded mode SHOULD become visible through one or more of:
- `HealthReport.status = "degraded"`
- `HealthReport.degraded_features`
- `AcceptanceResult.warnings`
- `QueryPlan.degraded_mode = true`
- `QueryPlan.fallback_reason`
- lowered `QueryEvidenceLevel`
- `FailureResult` when a forced strategy or capability cannot be honored

### 7.4 Required behavior under degraded mode

**For strategy="auto"**
The system MAY fallback to a weaker route, but MUST expose:
- chosen strategy
- fallback reason
- degraded mode

**For forced strategy requests**
If the requested route cannot be honored:
- return `FailureResult`, or
- only fallback if explicit contract allows it

*Silent substitution is forbidden.*

**For intent="audit"**
The system SHOULD be more conservative:
- downgrade confidence aggressively when evidence weakens
- prefer fewer trustworthy results over many weak ones
- surface provenance gaps
- avoid presenting degraded results as equivalent to healthy-path results

---

## 8. Rejection vs Failure Semantics

This distinction is non-negotiable.

### 8.1 Rejection

A rejection means:

*the system intentionally refused an operation according to rule, policy, trust posture, or governance logic.*

It is not a crash.
It is not a missing dependency.
It is an act of enforcement.

Canonical shape:

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
    evidence: list
    remediation: list[str]
    metadata: dict
```

### 8.2 Failure

A failure means:

*the system could not perform the requested operation due to runtime or dependency conditions.*

Canonical shape:

```python
class FailureResult(TypedDict):
    ok: Literal[False]
    kind: Literal["failure"]
    category: Literal["dependency", "storage", "runtime", "timeout", "capability"]
    code: str
    message: str
    retryable: bool
    component: str
    metadata: dict
```

### 8.3 Hard rules
- Dependency outages MUST NOT be represented as rejections.
- Policy blocks MUST NOT be represented as failures.
- Consumers MUST be able to distinguish governance posture from runtime instability.

### 8.4 Examples

**Rejection**
- contradiction detected
- taint threshold exceeded
- policy blocked scope
- deprecated write path blocked
- quorum denied under governance rules

**Failure**
- embedder offline
- database lock timeout
- ledger I/O failure
- capability disabled at runtime
- event dispatch failure
- verification scope invalid due to malformed input

---

## 9. Integrity Semantics

Integrity is the public representation of structural validity around stored or inferred state.

### 9.1 Integrity does not mean truth

Integrity means:
- chain structure is consistent
- cryptographic or structural checks passed
- the record has not obviously drifted from its expected lineage or checkpoint basis

It does NOT mean:
- the content is philosophically true
- the source is omniscient
- the model never hallucinated upstream

### 9.2 Public integrity states

```python
from typing import Literal, TypedDict


class IntegrityState(TypedDict):
    status: Literal["unknown", "partial", "verified", "failed", "stale"]
    reason: str
```

### 9.3 Semantics
- **unknown** — no integrity evaluation available
- **partial** — only subset or limited path checked
- **verified** — requested or linked integrity checks passed
- **failed** — structural check failed
- **stale** — integrity state exists but is too old or insufficiently current for strong claims

### 9.4 Verification scopes

Public verification SHOULD distinguish scope:
- fact
- project
- tenant
- time range
- tx chain

### 9.5 Verify result expectations

A `VerifyResult` SHOULD report:
- requested scope
- checked item count
- failed item count
- integrity state
- legacy path involvement
- full vs partial verification

### 9.6 Legacy path warning

If integrity verification depends on legacy hash or schema paths, that fact SHOULD be surfaced in:
- warnings
- metadata
- verify result notes

*Because “verified” by archaeological compatibility is not the same as “verified” on clean modern rails.*

---

## 10. Taint Semantics

Taint models downstream trust contamination or risk inheritance.

### 10.1 Definition

Taint is a trust degradation signal that propagates through dependency or causality structures when upstream inputs, decisions, or facts are suspect, contradictory, compromised, or insufficiently trustworthy.

### 10.2 Taint is not binary

Public surfaces SHOULD expose at least a small number of taint states.

```python
from typing import Literal, TypedDict


class TaintState(TypedDict):
    status: Literal["none", "low", "medium", "high", "unknown"]
    reason: str
```

### 10.3 Suggested interpretation
- **none** — no active taint detected
- **low** — weak taint signals or low-confidence contamination path
- **medium** — meaningful contamination risk
- **high** — serious contamination risk; downstream trust strongly reduced
- **unknown** — taint system unavailable or insufficiently evaluated

### 10.4 Public behavior
- high taint SHOULD strongly affect confidence, evidence level, or rejection posture
- unknown taint MUST NOT be silently treated as none
- `intent="audit"` SHOULD surface taint explicitly when requested or relevant

### 10.5 Open vs premium guidance
- Open tier MAY expose current taint visibility
- Premium tier MAY expose persistent taint propagation, policy thresholds, and exportable taint lineage

*This split is acceptable only if open tier still exposes enough truth not to mislead consumers.*

---

## 11. Query Trust Semantics

### 11.1 Query is not just retrieval

A query result is a trust-bearing object containing:
- content
- confidence
- provenance posture
- routing plan
- degradation context
- optional taint/trace posture

### 11.2 Required semantics for QueryResult

**If strategy="auto":**
- `plan.selected_strategy` MUST be present

**If fallback materially changes route:**
- `plan.fallback_used = true`
- `plan.fallback_reason` SHOULD be present

**If runtime degradation materially affects the result:**
- `plan.degraded_mode = true`

### 11.3 Intent-specific expectations

**lookup**
Optimize for concrete retrieval with reasonable trust visibility.

**explore**
Optimize for breadth, relation, and expansion, but still expose degradation and provenance limits.

**audit**
Optimize for trust clarity:
- prefer fewer, stronger results
- expose evidence level clearly
- expose provenance gaps
- degrade conservatively
- avoid overconfident ranking of weakly sourced items

### 11.4 Confidence vs trust

Confidence score is not equivalent to trust.

A result may have:
- high lexical or vector score
- low evidence level
- unknown integrity
- medium taint
- degraded routing path

*Consumers MUST be able to distinguish “matched strongly” from “trusted strongly.”*

---

## 12. Write Path Trust Semantics

### 12.1 A successful write is not just storage

A successful write means the system:
- accepted the operation under current trust policy
- completed storage path
- returned any required warnings
- attached operation metadata where applicable

### 12.2 A rejected write is governance, not breakage

Examples:
- contradiction with canonical fact
- taint threshold exceeded
- compliance scope violation
- policy forbids raw write into protected tenant
- deprecated path blocked

### 12.3 A write under degraded mode

If the write succeeds under degraded conditions, the system SHOULD warn when the degradation is materially relevant.

Examples:
- accepted without vector enrichment
- accepted while compliance export unavailable
- accepted while downstream event dispatch degraded

*Do not pretend the path was pristine if it was limping.*

---

## 13. Coordination Trust Semantics

Coordination is the noisiest place to hallucinate certainty. Do not.

### 13.1 Consensus is not omniscience

Public consensus results should reflect:
- participating agents
- available liveness posture
- confidence/weighting basis where exposed
- degraded conditions
- quorum state

### 13.2 Required caution zones

The following conditions SHOULD reduce coordination trust or trigger warnings:
- stale agents
- liveness unknown
- degraded event visibility
- mixed legacy vote paths
- insufficient quorum
- disabled consensus capability
- incomplete tracking path

### 13.3 Coordination truth posture

Do not present a coordination result as fully trustworthy when:
- liveness is missing
- tracking is partial
- vote schema is in deprecation transition
- event bus evidence is missing where expected

*A swarm with no pulse is just a rumor.*

---

## 14. Runtime Truth Semantics

### 14.1 health() is operational truth, not decoration

`health()` must be actionable.

Consumers should be able to use it to:
- decide whether to force a strategy
- detect degraded mode
- gate compliance-sensitive operations
- switch UI states
- annotate logs or metrics

### 14.2 capabilities() is contractual truth

`capabilities()` defines what the runtime can actually do now.

*Documentation, licensing text, and roadmap prose do not override runtime flags.*

### 14.3 Contractual expectations

If a capability is disabled:
- forced use should fail clearly
- auto mode may fallback if allowed
- the result must not pretend premium behavior occurred

---

## 15. Trust-Aware Error Code Semantics

### 15.1 Rejection codes imply governance meaning

Examples:
- `ERR_CONTRADICTION`
- `ERR_TAINT_HIGH`
- `ERR_POLICY_BLOCK`
- `ERR_COMPLIANCE_SCOPE`
- `ERR_DEPRECATED_WRITE_PATH`

These should tell the integrator:
- why it was blocked
- where the block happened
- what to do next

### 15.2 Failure codes imply operational meaning

Examples:
- `ERR_EMBEDDER_UNAVAILABLE`
- `ERR_DB_LOCK_TIMEOUT`
- `ERR_LEDGER_IO`
- `ERR_EVENT_DISPATCH_FAILED`
- `ERR_COMPONENT_UNAVAILABLE`

These should tell the integrator:
- what broke
- whether retry makes sense
- whether degradation/fallback is possible

### 15.3 Code stability

Codes are part of the contract.
*Do not repurpose them because a naming whim passed through the building at 3 AM.*

---

## 16. Trust Semantics for Exports

### 16.1 Canonical export truth

The canonical export format SHOULD preserve:
- schema version
- identifiers
- trust signals
- integrity posture
- taint posture where available
- warnings
- capability/degraded hints where relevant

### 16.2 Export adapters

External dialect adapters MAY map canonical trust signals into:
- JSON-LD-ish representations
- compliance-specific shapes
- audit tool formats

But the canonical internal export truth SHOULD remain the source of meaning.

*Do not let the adapter become the theology.*

---

## 17. Non-Goals

This document does not claim:
- philosophical truth of content
- total elimination of model error
- formal proof guarantees unless explicitly implemented
- perfect liveness in coordination
- omniscient provenance in all retrieval paths
- deterministic replay from partial working-memory exports

*This is a trust contract, not a messiah contract.*

---

## 18. Final Position

The public system must make one thing unmistakably clear:

*a result is not just returned; it is situated.*

Its route, evidence, degradation, integrity posture, taint posture, and governance status must be legible enough that an external consumer can decide what to do next without guessing.

That is the threshold between “clever memory system” and “infrastructure that can be trusted under pressure.”
