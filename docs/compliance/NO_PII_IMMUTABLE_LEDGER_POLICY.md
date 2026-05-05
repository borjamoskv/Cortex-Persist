# No-PII Immutable Ledger Policy

Status: draft

M6 adds a strict pre-persistence policy for immutable ledger events. The policy
is designed to prevent direct identifiers from entering hash-chained ledger
payloads. It does not delete or rewrite historical ledger rows.

## Runtime Contract

`LedgerWriter` can be configured with `LedgerPIIPolicy`. When enabled, the
writer validates the event before origin signatures, replay checks, hash
calculation, SQLite insert, and enrichment enqueue.

If validation fails:

- no `ledger_events` row is inserted;
- no replay reservation is created;
- no enrichment job is created;
- the rejection error names only the field path, not the rejected value.

## Allowlisted Metadata

Strict metadata keys are allowlisted. The default allowlist is:

- `decision_ref`
- `parent_decision_id`
- `payload_ref`
- `project`
- `reason_code`
- `risk_ref`
- `subject_ref`
- `taint`
- `tenant_id`
- `trace_ref`

Unknown metadata keys are rejected in strict mode. Direct-identifier key names
such as `email`, `phone`, `full_name`, `passport`, `iban`, and `ssn` are always
rejected.

## Direct Identifier Detection

The policy rejects common direct identifiers in string fields:

- email addresses;
- E.164-like phone numbers;
- common dashed phone numbers;
- US SSN shape;
- IBAN-like account identifiers;
- IPv4 addresses.

Cryptographic opaque values such as hashes, public keys, and signatures are not
scanned as plaintext identifiers.

## Export Boundary

Public forensic ledger export validates events with the same no-direct-
identifier guard before writing `events.jsonl`. Export rejection errors do not
include the sensitive value.

## Operator Notes And Reports

`scrub_text()` is available for operator-note and report surfaces that need to
display human-entered text. It replaces detected direct identifiers with
`[REDACTED]`.

## Current Limitations

This is not a full DLP engine and does not prove that pseudonymous references
cannot be linked outside CORTEX. Hashes or HMACs can still be personal data
under GDPR if they are linkable by a controller with auxiliary data.

Historical ledger rows are not rewritten. If direct identifiers already entered
an immutable ledger, remediation must use legal hold, access restriction,
crypto-shredding of associated fact payloads where possible, and documented
residual risk.
