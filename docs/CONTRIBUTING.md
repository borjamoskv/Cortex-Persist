# CONTRIBUTING.md — Deep Change Protocols

Package: cortex-persist v0.3.0b1
Engine: v8
License: Apache-2.0
Python: >=3.10

## Scope

This document defines deep change protocols for critical trust surfaces.

For local setup, test commands, and the basic pull request flow, see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

For repository-wide invariants, see [`../AGENTS.md`](../AGENTS.md).

## Trust-Surface Principle

Changes affecting schema, ledger continuity, tenant isolation, policy, guards,
or async transactional correctness are not routine edits. They are trust events
and must be reviewed as such.

## Schema Change Protocol

Before changing schema or migrations:

1. Read existing migrations first.
2. Identify whether the change is additive, destructive, or behavior-altering.
3. Check backward compatibility and upgrade path assumptions.
4. Document rollback constraints explicitly.
5. Review impact on:
   - persistence behavior
   - tenant isolation
   - search/index behavior
   - auditability
   - migration safety in production

Schema changes must never be treated as cosmetic refactors.

## Ledger Change Protocol

Before changing `ledger.py` or any hash-continuity behavior:

1. Read current ledger tests first.
2. Identify whether the change affects:
   - hash derivation
   - append continuity
   - verification logic
   - replay or historical verification
3. Add or update tests for continuity guarantees.
4. Document the effect on historical validation behavior.
5. Treat any change that can invalidate prior chain assumptions as a trust event.

If a change can break historical verifiability, it requires explicit reviewer attention.

## Guard and Validation Protocol

Before changing guards, gate logic, or validation boundaries:

1. Identify the precise validation layer being modified:
   - contradiction detection
   - dependency validation
   - input-hardening or injection-detection controls
   - policy admission
   - schema/type validation
2. Confirm whether the change narrows or widens acceptance conditions.
3. Add tests for:
   - valid acceptance
   - expected rejection
   - regression edge cases
4. Review downstream impact on durable state mutation.

Do not silently downgrade rejection into permissive behavior.

## Async Change Protocol

Before changing async code paths:

1. Confirm no blocking calls are introduced.
2. Verify timeout behavior.
3. Verify cancellation behavior.
4. Verify cleanup of connections, cursors, locks, and resources.
5. Check transaction boundaries for partial-write risk.
6. Review impact on daemon, API, and concurrent callers where applicable.

Async correctness is part of the trust surface.

## API Change Protocol

Before changing route contracts, request/response surfaces, or public API behavior:

1. Confirm request shape and response shape remain intentional.
2. Update typed surfaces where applicable.
3. Add or update route tests.
4. Update docs if public behavior changes.
5. Review parity with CLI or MCP surfaces where relevant.
6. Review auth, tenant, and validation implications.

## Tenant Isolation Protocol

Before changing read/write/query paths:

1. Confirm tenant scoping remains explicit.
2. Check search and recall paths for accidental cross-tenant behavior.
3. Review caches, indexes, and derived views for isolation leakage.
4. Add tests where tenant filtering is part of the behavior contract.

A correct feature with broken isolation is still broken.

## Auditability Protocol

Before changing write paths or persistence-adjacent flows:

1. Confirm audit-relevant events still emit.
2. Confirm cryptographic or ledger-adjacent steps still occur in the intended order.
3. Review whether a failed validation aborts early enough.
4. Check whether side effects occur only after acceptance, not before.

The system should prefer inspectable failure over silent mutation.

## Documentation Update Protocol

Update docs when you change:

- trust boundaries
- merge or validation semantics
- write-path order
- public APIs
- CLI behavior
- migration or rollback expectations
- operational commands or runtime procedures

Relevant documents include:

- [`../AGENTS.md`](../AGENTS.md)
- [`./SECURITY_TRUST_MODEL.md`](./SECURITY_TRUST_MODEL.md)
- [`./ARCHITECTURE.md`](./ARCHITECTURE.md)
- [`./OPERATIONS.md`](./OPERATIONS.md)

## Review Gate for Trust Events

A trust-surface change is incomplete if it lacks any of:

- tests for modified behavior
- type coverage for public surfaces
- migration impact review for schema changes
- ledger continuity review for hash-surface changes
- tenant-isolation review for data-path changes
- async correctness review for concurrency-sensitive changes
- documentation update where public or operational behavior changed

## Merge Rule

Changes affecting schema, ledger continuity, tenant isolation, policy, guards,
or async transactional correctness are not routine edits. They are trust events
and must be reviewed as such.
