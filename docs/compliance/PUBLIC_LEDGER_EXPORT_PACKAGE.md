# Public Ledger Export Package

Status: draft

This document defines the forensic ledger export package produced for
independent offline verification. The package is evidence packaging only: it
does not reserve replay nonces, prove source-database completeness, or export
fact payloads. Runtime strict origin signing is defined in
[`M4_ORIGIN_SIGNATURES_STRICT_MODE.md`](M4_ORIGIN_SIGNATURES_STRICT_MODE.md).

## Required Artifacts

A `public-v1-strict` export directory contains:

- `events.jsonl`: canonical JSON Lines ledger events.
- `manifest.json`: signed manifest over package artifacts and event range.
- `public-keys.json`: actor and export-authority public key registry.
- `key-events.jsonl`: reserved key lifecycle event stream.
- `schema.json`: event schema/profile descriptor.
- `verification-profile.json`: canonicalization, hash, signature, and Merkle
  profile descriptor.

When requested, the exporter also writes:

- `verification-report.json`: deterministic output from the offline verifier.

The package must not contain `facts.jsonl`, plaintext fact payload files, private
keys, secrets, or executable files. Fact export is a separate product surface
with separate retention, redaction, and erasure controls.

## Manifest Scope

`manifest.json` includes:

- export identity, tenant, stream, purpose, environment, creator, and creation
  time;
- event count and sequence/time range;
- SHA-256 hashes of `events.jsonl`, `public-keys.json`, `key-events.jsonl`,
  `schema.json`, and `verification-profile.json`;
- first and last event hash;
- `merkle-profile-v1` root over event hashes;
- Ed25519 signature by an export authority key.

The manifest signature scope is:

```text
Ed25519.sign(export_authority_private_key, canonical_json(manifest without signature))
```

## Event Payload Boundary

The public ledger export may include references to encrypted or externally
controlled fact material, for example `payload_ref` or `subject_ref`.

The export builder rejects common inline fact payload keys inside event
`detail`:

- `content`
- `payload`
- `plaintext`
- `fact_content`

This is a guardrail for forensic packaging, not a complete PII detector. M6 is
the enforcement milestone for immutable-ledger no-PII policy.

## Guarantee Split

If the optional verifier report is generated, it preserves the offline guarantee
split:

- `integrity_verified`
- `origin_authenticity_verified`
- `authority_verified`
- `replay_consistency_verified`
- `temporal_consistency_verified`
- `online_freshness_verified`
- `completeness_verified`
- `truth_verified`

For offline exports, `online_freshness_verified` remains false. The verifier
does not assert that event contents are true; `truth_verified` remains false by
default.

## Legacy Streams

Legacy-v0 exports are explicitly integrity-only. They may include deterministic
legacy hash vectors and a `LIMITATIONS.txt` note, but they do not claim origin
authenticity, manifest completeness, online freshness, or truth verification.

## Current Limitations

M3 assumes strict public events already carry `public-v1-strict` fields,
including `origin_signature`, `actor_key_id`, `nonce`, and hash-chain
continuity.

M3 does not:

- sign ledger events on behalf of actors;
- reject unsigned runtime writes before persistence;
- create actor-key authorization policy;
- reserve or consume replay nonces;
- prove that a source database contains no omitted events;
- export plaintext facts or reconstruct fact contents.

Those controls belong to later milestones, especially M4, M5, and M6.

M4 adds runtime origin-signature admission for `LedgerWriter` strict mode. M5
remains responsible for durable replay nonce reservation, and M6 remains
responsible for immutable-ledger no-PII enforcement.
