# Public Test Vectors

Status: draft

These vectors freeze expected hash, signature, manifest, and report behavior for
future public verifier implementation. Test keys are for fixtures only and must
not be used in production.

## Legacy-v0

Vector 1:

```text
prev_hash: GENESIS
project: loan-risk
action: store
detail_json: {"fact_type":"decision"}
timestamp: 2026-05-04T12:00:00+00:00
expected_hash: c607a9af884d602f415e997187da89c95b773d4304e848dce697807a3c349e2d
```

Vector 2:

```text
prev_hash: c607a9af884d602f415e997187da89c95b773d4304e848dce697807a3c349e2d
project: loan-risk
action: deprecate
detail_json: {"fact_id":1,"reason":"operator override"}
timestamp: 2026-05-04T12:01:00+00:00
expected_hash: 991cd9919bbb74b86c2294e018c462107337241d5a581eb77376506c024eba6c
```

Legacy vectors prove integrity only.

## Public-v1 Strict

The strict vector includes a nonce, `fact.store` permission, an event origin
signature, an export authority with `ledger.export`, a signed manifest, exact
file hashes, and a Merkle root.

Expected event hash:

```text
518375b3ebdb916e0a779eb2baa6c9fcfbe4ae246a18eda9b4dfad0f32d2d59b
```

Expected event signature:

```text
knDsL1dfQ4L4duUa7iR4nwh0IUnppgwoZj6EWjOQsGSNviQ116H-OKdKSNMvnS57uzh_JZX9dbxPqKB0C6lNBw
```

Expected manifest signature:

```text
_mq89nDDZiTdV18MGZdISnA_hMwWdeKtDhT-S6ENwWmbGK_eN2qh447VrXECUDAUooOs3VDrTCvraR9ru63lAA
```

Expected strict report:

```json
{
  "result": "VALID_FULL_STRICT",
  "guarantees": {
    "integrity_verified": true,
    "origin_authenticity_verified": true,
    "authority_verified": true,
    "replay_consistency_verified": true,
    "temporal_consistency_verified": true,
    "online_freshness_verified": false,
    "completeness_verified": true,
    "truth_verified": false
  }
}
```

## Negative Fixtures

- Missing `nonce`: strict schema failure.
- Missing manifest: valid with limitations only; completeness is false.
- Tampered detail: hash mismatch.
- Bad manifest signature: manifest signature failure.
