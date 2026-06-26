# ADR 0002: Cryptographic Evidence Model

## Status
Accepted

## Context
CORTEX Persist aims to provide a verifiable digital evidence platform achieving maximum security and compliance ratings (e.g., EU AI Act, OWASP LLM). We need a core structural representation for every system event that guarantees non-repudiation, immutability, and temporal verification.

## Decision
We define a formal Cryptographic Evidence Model for all state mutations. Every event persisted must conform to the following schema before entering the Master Ledger:
- `event_id`: Unique identifier (UUIDv4 or SHA3).
- `timestamp`: ISO-8601 UTC timestamp.
- `actor`: System, agent, or user identifier.
- `source`: The module or boundary originating the fact.
- `payload_hash`: SHA-256 hash of the JSON-normalized event payload.
- `prev_hash`: SHA-256 hash of the previous event (maintaining the hash chain).
- `signature`: Ed25519 signature of the `payload_hash` + `timestamp`.

## Consequences
- **Positive**: Establishes a tamper-evident chain of custody. Forms the foundation for Phase 1 (Enterprise Cryptography) features like RFC3161 timestamps and Sigstore/Rekor integration.
- **Negative**: Increases the computational and storage overhead for every write operation. Requires strict adherence to the Write-Path Contract (Saga Pattern).
