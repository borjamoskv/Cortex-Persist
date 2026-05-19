# Public Ledger Verifier Spec

Status: draft

This document defines the minimum contract for an offline public verifier for
CORTEX ledger exports. The verifier must validate exported bytes without
accessing SQLite, network services, or a running CORTEX process.

The matching package layout is documented in
[`PUBLIC_LEDGER_EXPORT_PACKAGE.md`](PUBLIC_LEDGER_EXPORT_PACKAGE.md).

## Profiles

- `legacy-v0`: verifies the current transaction hash shape for legacy data. It
  provides integrity-only evidence.
- `public-v1-strict`: verifies event hash, origin signature, actor authority,
  replay consistency, temporal consistency, manifest-declared completeness, and
  Merkle root.

## Public-v1 Strict Event Fields

Strict events require:

- `schema_version`
- `stream_id`
- `tenant_id`
- `sequence`
- `event_id`
- `nonce`
- `issued_at`
- `recorded_at`
- `actor_id`
- `actor_key_id`
- `action`
- `project`
- `target`
- `detail`
- `prev_hash`
- `hash_alg`
- `hash`
- `signature_alg`
- `origin_signature`

Unknown critical fields are rejected in strict mode unless a future profile
defines an extension namespace.

## Canonicalization

The strict profile uses byte-exact UTF-8 canonical JSON:

- reject duplicate JSON keys;
- reject floats, `NaN`, and `Infinity`;
- sort object keys lexicographically;
- use compact separators;
- do not normalize Unicode.

## Hash And Signature Scope

Event hash:

```text
SHA-256(canonical_json(event without hash and origin_signature))
```

Event origin signature:

```text
Ed25519.sign(actor_private_key, canonical_json(event without origin_signature))
```

Manifest signature:

```text
Ed25519.sign(export_authority_private_key, canonical_json(manifest without signature))
```

## Merkle Profile v1

For each event hash:

```text
leaf = SHA-256("CORTEX-MERKLE-LEAF-v1:" + event_hash_hex)
node = SHA-256("CORTEX-MERKLE-NODE-v1:" + left_hash_hex + right_hash_hex)
```

Odd leaves are promoted unchanged. A single-event tree root is its leaf hash.

## Report Guarantees

Reports must split guarantees:

- `integrity_verified`
- `origin_authenticity_verified`
- `authority_verified`
- `replay_consistency_verified`
- `temporal_consistency_verified`
- `online_freshness_verified`
- `completeness_verified`
- `truth_verified`

For offline historical exports, `online_freshness_verified` is false. By
default, `truth_verified` is false.

## CLI Contract

The read-only verifier CLI accepts either a `public-v1-strict` export directory
or a legacy vector file:

```bash
cortex verify-ledger-export ./export-dir
cortex verify-ledger-export ./legacy_v0_vector_1.json
```

The command must:

- read exported files only;
- avoid SQLite, network calls, and a running CORTEX process;
- emit deterministic JSON with `profile`, `result`, `guarantees`, `counts`,
  `artifacts`, `event_hashes`, `errors`, and `warnings`;
- exit `0` for `VALID_FULL_STRICT`;
- exit `1` for `INVALID`;
- exit `6` for `VALID_INTEGRITY_ONLY` and `VALID_WITH_LIMITATIONS`.
