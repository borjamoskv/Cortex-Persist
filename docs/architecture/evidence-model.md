# Evidence Model Definition

## Overview
This schema formalizes the data structure required to persist an event in the CORTEX Persist Master Ledger. It is the core primitive for Phase 1 enterprise cryptography.

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CORTEX Persist Evidence Model",
  "type": "object",
  "properties": {
    "event_id": {
      "type": "string",
      "description": "Unique UUIDv4 or SHA3 hash of the event contents."
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp of event generation."
    },
    "actor": {
      "type": "string",
      "description": "Identity of the agent, user, or daemon triggering the mutation."
    },
    "source": {
      "type": "string",
      "description": "The specific CORTEX module or subsystem (e.g., 'cortex.engine.crystallizer')."
    },
    "payload_hash": {
      "type": "string",
      "description": "SHA-256 hash of the normalized JSON representation of the mutated state/facts."
    },
    "prev_hash": {
      "type": "string",
      "description": "SHA-256 hash of the immediate predecessor event in the tenant's ledger chain."
    },
    "signature": {
      "type": "string",
      "description": "Ed25519 cryptographic signature generated over (payload_hash + timestamp + prev_hash)."
    }
  },
  "required": [
    "event_id",
    "timestamp",
    "actor",
    "source",
    "payload_hash",
    "prev_hash",
    "signature"
  ],
  "additionalProperties": false
}
```

## Validation Rules
1. **Chain Continuity**: The `prev_hash` must exactly match the `event_id` or `payload_hash` (depending on chain construction) of the last committed event.
2. **Signature Validity**: The `signature` must be verifiable using the public key associated with the `actor`.
3. **Immutability**: Once written, this structure is append-only. Modification breaks the `prev_hash` chain of all subsequent events.
