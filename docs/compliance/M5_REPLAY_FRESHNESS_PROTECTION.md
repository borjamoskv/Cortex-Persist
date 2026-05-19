# M5 Replay And Freshness Protection

Status: draft

M5 adds online replay admission for strict ledger writes. It prevents a signed
event from being replayed as a fresh action and separates live admission checks
from historical offline verification.

## Admission Storage

`ledger_replay_admissions` records accepted live events with:

- `tenant_id`
- `event_id`
- `nonce`
- `request_hash`
- `payload_hash`
- `ledger_event_id`
- `actor_key_id`
- `action`
- `issued_at`
- `accepted_at`

The table enforces tenant-scoped uniqueness with:

- `ux_ledger_replay_tenant_event_id` on `(tenant_id, event_id)`
- `ux_ledger_replay_tenant_nonce` on `(tenant_id, nonce)`

`ledger_events.event_id` remains the ledger row primary key. Replay admission is
tenant-scoped; callers should still issue globally collision-resistant event
ids for ledger row portability.

## Atomicity

Replay reservation happens inside the same SQLite transaction as the
`ledger_events` insert. If the ledger write rolls back, the reservation rolls
back. Origin-auth and online freshness validation happen before reservation, so
failed validation does not consume an event id or nonce.

`EnrichmentQueue` remains a post-commit side effect. An idempotent retry returns
the already-accepted event id and does not reinsert the ledger row or enqueue a
second enrichment job.

## Retry Semantics

Exact retry means the same tenant, event id, nonce, and canonical request hash.
It returns the original event id without re-executing the write.

Mutated retry means the same tenant plus same event id and nonce but a different
canonical request hash. It is rejected with `replay_retry_mutated`.

Same tenant plus duplicate event id is rejected with
`replay_event_id_duplicate`. Same tenant plus duplicate nonce is rejected with
`replay_nonce_duplicate`.

## Online Freshness

Live agent admission checks `origin.issued_at` against the local admission
clock:

- events newer than `now + future_skew_seconds` are rejected;
- events older than `now - max_age_seconds` are rejected.

The default policy uses a five minute max age and a thirty second future skew.
Tests inject a fixed clock. Operators may inject a different
`ReplayAdmissionPolicy` where stricter or looser live windows are required.

## Offline Separation

Offline historical verifier reports keep `online_freshness_verified: false`.
Missing manifests can still produce `VALID_WITH_LIMITATIONS` for historical
inspection. Online batch import is stricter: `validate_batch_import_manifest`
requires `manifest.json` and a `VALID_FULL_STRICT` verifier result before a
batch can be admitted as live replay input.

## Migration And Rollback

Migration 026 adds the replay admission table and indexes. The rollback policy
is additive: downgrades may leave the table in place because older readers
ignore it, while dropping it would erase replay-admission evidence.
