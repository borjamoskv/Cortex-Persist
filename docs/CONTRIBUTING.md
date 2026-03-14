# Contributing — CORTEX Persist

> How to contribute without breaking trust surfaces.
>
> Related: [`AGENTS.md`](../AGENTS.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`SECURITY_TRUST_MODEL.md`](SECURITY_TRUST_MODEL.md)

---

## Branch Workflow

1. Create a feature branch from `main`.
2. Keep branches short-lived — merge or close within days, not weeks.
3. Rebase on `main` before opening a PR.

---

## Commit Style

- Use imperative mood: "Add guard for X", not "Added guard for X".
- One logical change per commit.
- Reference issue numbers where applicable.

---

## Required Tests

Every PR must include tests for modified behavior. Tests mirror `cortex/` structure in `tests/`.

```bash
# Run full suite
pytest tests/ -v --cov=cortex

# Run fast subset (no torch/embedding imports)
pytest tests/ -v -m "not slow"
```

---

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

- Guard behavior (injection, contradiction, dependency)
- Encryption/decryption flow
- Ledger continuity
- Audit trail emission
- Embedding/index side effects

---

## PR Acceptance Gate

A change is incomplete if it lacks any of:

- Tests for modified behavior
- Type coverage for public surfaces
- Migration impact review (if schema touched)
- Ledger/audit impact review (if trust surface touched)
- Async correctness review (if concurrency-sensitive path touched)

---

## Quality Gates

```bash
# Lint
ruff check cortex/

# Type check
pyright cortex/

# Tests with coverage
pytest tests/ -v --cov=cortex
```

All three must pass before merge. CI enforces this via `.github/workflows/quality_gates.yml`.

---

*CORTEX Persist · `cortex-persist` v0.3.0b1*
