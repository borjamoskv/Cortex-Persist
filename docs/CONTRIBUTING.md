# CONTRIBUTING.md — Deep Change Protocols

Package: cortex-persist v0.3.0b1 · Engine: v8
License: Apache-2.0 · Python: >=3.10

## Scope

This document defines deep change protocols for critical trust surfaces.

For local setup, test commands, and the basic pull request flow, see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

For repository-wide invariants, see [`../AGENTS.md`](../AGENTS.md).

## Schema Changes

Schema changes are **irreversible in production**. Before modifying:

1. Create a new migration file in `cortex/migrations/`.
2. Test forward migration on a fresh database.
3. Document rollback constraints (or confirm rollback is impossible).
4. Assess impact on existing data and downstream queries.
5. Never modify existing migration files — only add new ones.

---

## Ledger Changes

`ledger.py` is the cryptographic trust chain. Before modifying:

1. Read and understand the hash chain mechanism.
2. Run the full ledger verification test suite.
3. Ensure hash continuity is preserved across all code paths.
4. Document any changes to the hashing algorithm or chain structure.
5. Get explicit review from a trust-surface maintainer.

---

## Async Changes

CORTEX is async-first. Before modifying async code:

1. Verify no blocking calls (`time.sleep()`, synchronous I/O) exist in async paths.
2. Test cancellation behavior and timeout handling.
3. Use `asyncio.to_thread()` for any unavoidable blocking operations.
4. Verify connection pool behavior under concurrent access.

---

## API Changes

REST API endpoints are external contracts. Before modifying:

1. Maintain backward compatibility unless a breaking change is explicitly approved.
2. Update OpenAPI schema and route tests.
3. Verify authentication and tenant isolation on new endpoints.
4. Test rate limiting behavior.

---

## Write-Path Changes

Any change to the store/write path must validate:

- Guard behavior (contradiction, dependency, and injection-detection surfaces)
- Encryption/decryption flow
- Ledger continuity
- Audit trail emission
- Embedding/index side effects

---

## Merge Rule

Changes affecting schema, ledger continuity, tenant isolation, policy, guards,
or async transactional correctness are not routine edits. They are trust events
and must be reviewed as such.
