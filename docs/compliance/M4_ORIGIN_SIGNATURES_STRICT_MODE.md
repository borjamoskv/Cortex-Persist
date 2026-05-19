# M4 Origin Signatures Strict Mode

Status: draft

M4 adds runtime admission checks for strict ledger events before persistence.
It turns origin fields from export-only evidence into a write-time contract:
agent or external events in strict mode must carry a valid Ed25519 origin
signature, an actor key, a tenant binding, a namespaced action, a payload hash,
a nonce, and an issued timestamp.

## Admission Contract

Strict admission rejects the event before opening the ledger write transaction
when any origin-auth control fails. Rejected events do not create:

- a `ledger_events` row;
- an enrichment job;
- a consumed nonce or other replay side effect;
- a downstream semantic enrichment side effect from `LedgerWriter`.

Nonce reservation is implemented by M5 replay admission. M4 verifies nonce
presence in the signed envelope and deliberately performs no durable nonce
mutation before origin authenticity succeeds.

## Signed Envelope

The runtime envelope is stored under `LedgerEvent.origin` and contains:

- `actor_id`
- `actor_key_id`
- `tenant_id`
- `action`
- `payload_hash`
- `nonce`
- `issued_at`
- `signature_alg`
- `hash_alg`
- `origin_signature`

`payload_hash` is:

```text
SHA-256(canonical_json(event without prev_hash, hash, and origin))
```

`origin_signature` is:

```text
Ed25519.sign(actor_private_key, canonical_json(event without prev_hash, hash, and origin_signature))
```

The hash and signature scope exclude ledger-chain fields because those are
assigned by the writer after admission. This lets the writer reject invalid
origin auth before persistence while still computing the normal chain hash.

## Key Registry

`OriginKeyRegistry` binds each `actor_key_id` to:

- the actor id;
- optional tenant id;
- Ed25519 public key material;
- namespaced permissions such as `fact.store`, `fact.deprecate`, or
  `ledger.export`;
- status and validity window.

Private keys never appear in public registry output. `OriginKeyRecord` stores
only the public key, and `to_public_dict()` serializes public material only.

## Key Status Semantics

`active` keys verify events issued inside their validity window.

`revoked` or `rotated` keys can verify historical events issued inside their
declared validity window. Events issued after `valid_until` are rejected. A
revoked key without a cutoff is rejected because offline verification cannot
bound the historical authority period.

`future`, disabled, unknown, or otherwise unsupported statuses are rejected.
Keys with `valid_from` after the event `issued_at` are rejected.

## Trust Semantics

Origin authenticity is attribution, not truth. A valid signature proves the
registered actor key signed the event scope and was authorized for the action at
the event time. It does not prove the event content is factually true, complete,
fresh online, or free of later operational compromise. `truth_verified` remains
false unless a future truth-verification mechanism explicitly proves it.
