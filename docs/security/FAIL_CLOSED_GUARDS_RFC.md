# Fail-Closed Guards RFC

Status: Proposed
Owner: security
Related: #99

## Problem

The current guard layer appears to contain at least one of these failure modes:

1. Required guards can fail open by logging and continuing.
2. High-severity contradictions may be detected but not enforced.
3. Validation paths may be advertised but unreachable in production.
4. Optional and required guards are not operationally separated.

This creates security theater: policy exists, but write-path integrity is not guaranteed.

## Goals

- Required guards MUST fail closed.
- Optional guards MAY fail open, but MUST emit structured telemetry.
- High-severity contradiction results MUST block write-path.
- Dead validation paths MUST be either implemented end-to-end or removed.
- Guard execution outcomes MUST be testable and auditable.

## Non-goals

- Rewriting the full guard framework in one pass.
- Changing the external API surface unless necessary.
- Adding ornamental complexity that does not reduce risk.

## Proposed model

### Guard classes

Every guard is classified as one of:

- `required`: integrity-critical, blocks write-path on exception or blocking result.
- `optional`: advisory, never authorizes a write on its own, exceptions are logged as telemetry.

### Guard outcome contract

Each guard SHOULD normalize into a common outcome object:

```python
@dataclass(slots=True)
class GuardOutcome:
    guard_name: str
    allowed: bool
    severity: Literal["low", "medium", "high", "critical"]
    code: str
    reason: str
    meta: dict[str, Any] = field(default_factory=dict)
```

### Enforcement contract

Pseudo-flow:

```python
for guard in guards:
    try:
        outcome = guard.evaluate(context)
    except Exception as exc:
        if guard.required:
            raise GuardExecutionError(guard.name) from exc
        log_optional_guard_failure(...)
        continue

    record_guard_outcome(outcome)

    if guard.required and not outcome.allowed:
        raise GuardBlockedWrite(outcome.guard_name, outcome.reason)

    if outcome.severity in {"high", "critical"} and not outcome.allowed:
        raise GuardBlockedWrite(outcome.guard_name, outcome.reason)
```

## Contradiction guard requirements

`ContradictionGuard` MUST block writes when:

- outcome.allowed == False, and
- severity is `high` or `critical`

Detection without enforcement is not acceptable for required integrity controls.

## Verifier path requirements

If `VerifierGuardAdapter` depends on `fact_type="code"`, one of these MUST happen:

1. `fact_type="code"` becomes a supported, tested, reachable production path.
2. `VerifierGuardAdapter` is removed from the advertised validation surface.

Half-wired validation paths are forbidden.

## Telemetry

Every guard run SHOULD emit structured telemetry:

- guard_name
- required
- allowed
- severity
- code
- elapsed_ms
- exception_class (if any)
- blocked_write (bool)

## Minimal implementation plan

### Phase 1

- Add required/optional classification.
- Enforce fail-closed for required guards.
- Enforce high-severity contradiction blocking.
- Add structured exceptions:
  - `GuardExecutionError`
  - `GuardBlockedWrite`

### Phase 2

- Normalize guard outcomes to a shared contract.
- Remove or complete dead verifier paths.
- Emit audit/ledger telemetry for each guard run.

## Acceptance criteria

- A required guard exception aborts write-path.
- A required guard blocking result aborts write-path.
- An optional guard exception does not authorize a write and is logged.
- A high-severity contradiction blocks write-path.
- No advertised verifier path remains unreachable.

## Test matrix

Required:

- `tests/integration_guards/test_fail_closed_required_guards.py`
- `tests/integration_guards/test_contradiction_blocks.py`
- `tests/integration_guards/test_verifier_path_real_or_removed.py`

Recommended additions:

- `tests/integration_guards/test_required_guard_exception_aborts_write.py`
- `tests/integration_guards/test_optional_guard_exception_logs_and_continues.py`
- `tests/integration_guards/test_high_severity_outcome_blocks_even_if_pipeline_continues.py`

## Migration note

If current behavior permits silent continuation after required-guard failure, this RFC is intentionally breaking. That break is the fix.
