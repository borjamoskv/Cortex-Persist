# Origin Signature Strict Mode

Status: draft

M4 adds a runtime origin-authenticity gate for ledger events. The gate is
opt-in at `LedgerWriter` construction so existing legacy ledger writes continue
to run until a deployer explicitly enables strict mode for an agent write path.

## Runtime Contract

Strict mode validates a `LedgerEvent` before opening the SQLite transaction.
If validation fails, no `ledger_events` row is inserted and no enrichment job is
created.

The event must carry an `origin` envelope:

- `actor_id`: actor that produced the event.
- `key_id`: registry key used to verify the event.
- `signature_alg`: currently `ed25519`.
- `signed_at`: timezone-aware timestamp.
- `nonce`: origin-generated uniqueness token.
- `signature`: base64url Ed25519 signature.

## Signature Scope

The signed payload is:

```text
canonical_json(event payload without hash and prev_hash, and with origin.signature removed)
```

The runtime hash-chain still commits the complete event payload after the
origin signature is attached. This means the ledger hash commits the signature,
and the origin signature commits the pre-persistence event intent.

## Key Registry

`OriginKeyRegistry` is an in-process registry of `OriginKeyRecord` entries.
Each record binds:

- `key_id`
- `actor_id`
- Ed25519 public key
- allowed actions
- key status
- optional validity window
- optional hardware-backed flag

Strict mode rejects:

- missing origin envelope;
- unsupported signature algorithm;
- actor/key mismatch;
- missing, inactive, not-yet-valid, or expired key;
- action not present in key permissions;
- invalid signature over the canonical scope.

## Current Limitations

M4 does not add durable key-registry storage, replay tables, freshness windows,
or nonce reservation. Those are M5 responsibilities.

M4 also does not assert that event content is true. It distinguishes origin
authenticity from content truth: a valid key can still sign false content, and
that must be handled by guard validation, review workflows, and downstream
forensic analysis.
