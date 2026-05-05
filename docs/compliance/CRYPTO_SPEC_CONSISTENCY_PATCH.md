# Crypto Spec Consistency Patch

Status: draft

This patch freezes the corrections required before implementing a public ledger
verifier. It exists to prevent test vectors and reports from overstating what a
profile proves.

## Strict Profile Corrections

`public-v1-strict` requires:

- `nonce` on every event.
- A signed manifest before `completeness_verified` can be true.
- A key registry entry for the event actor and the export authority.
- Namespaced permissions such as `fact.store` and `ledger.export`.
- Embedded manifest signatures under `manifest.signature`.

## Verification Semantics

Offline historical verification must separate:

- `replay_consistency_verified`: no duplicate event IDs or nonces were found in
  the export.
- `temporal_consistency_verified`: timestamps are internally consistent with
  key validity and the manifest.
- `online_freshness_verified`: an online admission freshness guarantee. This is
  false for historical offline exports.

`truth_verified` is false by default. Ledger integrity, signatures, and manifests
do not prove factual truth.

## Compatibility

`legacy-v0` vectors verify integrity only. They do not prove origin
authenticity or completeness unless separate evidence is provided.

Limited verification results should exit non-zero in strict automation contexts.
`VALID_INTEGRITY_ONLY` and `VALID_WITH_LIMITATIONS` are not equivalent to
`VALID_FULL_STRICT`.
