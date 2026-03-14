# SECURITY_TRUST_MODEL.md — CORTEX Persist

Package: cortex-persist v0.3.0b1 · Engine: v8
License: Apache-2.0 · Python: >=3.10

This document describes trust boundaries and cognitive/state-mutation risks.

For vulnerability disclosure policy and repository security reporting, see
[`../SECURITY.md`](../SECURITY.md).

## Purpose

This document defines the trust boundaries, guarantees, non-guarantees, and
verification surfaces of CORTEX Persist.

CORTEX is not secure because it stores data.
CORTEX is secure to the extent that it constrains who may mutate state, under
which conditions, with what auditability, and with what failure behavior.

## Security Posture

CORTEX assumes that non-trivial inputs may be malformed, deceptive, stale,
contradictory, or adversarial.

This includes:

- human input
- agent input
- upstream model output
- tool return values
- external API responses
- replayed or duplicated facts
- semantically valid but operationally dangerous content

Generative outputs are treated as proposals, not trusted state.

## Trust Boundary

The core trust boundary is the write path.

A proposal may only become durable state after crossing deterministic controls:

```text
proposal
  → guards
  → schema/type validation
  → policy/admission checks
  → encryption
  → ledger/audit recording
  → persistence
```

If any required control fails, the write aborts.

---

## Security Goals

CORTEX aims to provide:

- durable auditability of write behavior
- cryptographic continuity across facts
- encrypted storage of sensitive fact content and metadata
- tenant-aware data isolation
- deterministic rejection of structurally invalid inputs
- explicit validation boundaries between stochastic proposals and durable state
- inspectable failure rather than silent permissiveness

---

## Guarantees

CORTEX is designed to guarantee, within correct implementation and deployment:

### 1. Cryptographic Traceability

Persisted facts participate in a ledger continuity model through hash linking.

### 2. Encrypted At-Rest Storage

Sensitive content and metadata are encrypted before persistence.

### 3. Auditable Write Path

State mutation is expected to emit audit-relevant trace or log data.

### 4. Deterministic Structural Rejection

Inputs that fail required syntax, type, schema, or guard conditions should be rejected.

### 5. Tenant-Aware Isolation

Data operations are expected to preserve tenant boundary semantics.

### 6. Failure Locality

Invalid proposals should fail before contaminating downstream durable state.

---

## Non-Guarantees

CORTEX does not guarantee:

- semantic truth
- correctness of external models
- safety of upstream tools or providers
- correctness of external APIs
- absence of malicious intent in upstream sources
- correctness of business logic added outside trust boundaries
- safety if callers bypass guards, policy, or verification surfaces
- magical immunity from bad architecture layered above it

A cryptographically logged lie is still a lie. It is merely an auditable lie.

---

## Trust-Surface Threat Model

Representative threats include:

### Prompt / Instruction Injection

Inputs attempt to coerce the system into bypassing intended policy or semantics.

### Contradictory State Insertion

Inputs attempt to create durable memory that conflicts with validated prior state.

### Dependency Contamination

Proposal depends on false, stale, or unverifiable upstream assumptions.

### Silent Schema Drift

A change in structure weakens invariants without obvious runtime failure.

### Ledger Integrity Break

Hash continuity becomes invalid through bug, corruption, or unreviewed mutation.

### Replay / Duplication

Previously accepted facts are reintroduced in a way that degrades retrieval or
alters interpretation.

### Cross-Tenant Leakage

Data path accidentally leaks or merges tenant state.

### Async Safety Failure

Blocking or cancellation bugs produce state inconsistency or partial operations.

---

## Defense in Depth

CORTEX relies on layered control, not a single magic wall.

### Guards Layer

Examples include:

- contradiction guard
- dependency guard
- injection-detection and input-hardening controls

These operate before persistence and are intended to reject invalid or dangerous proposals.

### Policy / Gate Layer

Admission control and policy evaluation determine whether a write is even allowed
under the current actor, tenant, or environment.

### Crypto Layer

Encryption protects sensitive fact content and metadata at rest.

### Ledger Layer

Hash chaining provides continuity and tamper-evidence characteristics.

### Audit Layer

Audit records preserve post-hoc inspectability of critical mutations.

### Verification Layer

Formal or deterministic verifiers can be used where applicable to validate
invariants or reject invalid state transitions.

---

## Verification Membrane

The verification membrane is the boundary between generative uncertainty and
durable system state.

```text
LLM / tool proposal
  → guard validation
  → schema / type checks
  → policy gate
  → external verification where required
  → cryptographic logging
  → persistence
```

The membrane exists to convert unconstrained suggestion into constrained mutation.

---

## Ledger Integrity

`ledger.py` is a critical trust surface.

Its purpose is not branding. Its purpose is continuity.

### Required Properties

- append-like continuity semantics
- deterministic hash derivation behavior
- stable verification path
- test coverage for continuity assumptions
- explicit review for any change affecting link formation or verification

### Practical Rule

If a change can break historical verifiability, it is not a normal refactor.
It is a trust event.

---

## Encryption Model

Fact content and meta are encrypted at rest.

### Operational Meaning

- sensitive payloads must not be stored plaintext
- decryption occurs on authorized read path
- key handling must remain externalized and controlled
- secrets must not be reintroduced unencrypted into secondary stores

### Practical Rule (Encryption)

"Encrypted primary store + plaintext side channel" is not security. It is cosplay.

---

## Tenant Isolation

All new data operations should be tenant-aware by default.

### Risks

- implicit defaulting in unsafe contexts
- missing filters in read/search paths
- merged indexing or caching across tenant surfaces
- admin tooling that assumes single-tenant world state

### Expectation

Isolation must be explicit in APIs, search, caching, and persistence behavior.

---

## Audit Trails

The audit system exists for:

- forensic reconstruction
- compliance evidence
- mutation traceability
- incident investigation
- operational trust

Auditability is not a substitute for correctness.
It is the condition that makes correctness failures inspectable.

---

## Compliance Posture

CORTEX positions audit trails, decision traceability, and deterministic validation
as foundations for regulated AI environments, including EU AI Act-adjacent needs.

This should be stated carefully.

**Correct Claim:**
"The system is designed to support traceability, auditability, and constrained
state mutation."

**Weak Claim:**
"The system is compliant because we said 'compliance' near some hashes."

Compliance is not a vibe. It is evidence.

> For vulnerability disclosure and reporting, see [`SECURITY.md`](../SECURITY.md).

---

## Failure Domains

Critical failure domains include:

- write-path validation
- ledger integrity
- migrations
- tenant isolation
- async transactional correctness
- policy bypass
- index consistency
- external provider misclassification or drift

These domains deserve explicit review before release.

---

## Release Review Checklist for Trust Surfaces

Before release, review:

- guard behavior changes
- ledger continuity changes
- encryption path changes
- policy/gate changes
- migration safety
- tenant isolation behavior
- async cancellation/timeout behavior
- audit event completeness
- API surfaces that can mutate state

---

## Guiding Rule

CORTEX does not make models truthful.
It reduces their freedom to contaminate persistent state.

---

## Related Documents

- [`../SECURITY.md`](../SECURITY.md)
- [`../AGENTS.md`](../AGENTS.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`AXIOMS.md`](AXIOMS.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`OPERATIONS.md`](OPERATIONS.md)
