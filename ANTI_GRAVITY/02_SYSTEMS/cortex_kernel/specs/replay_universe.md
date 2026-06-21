# Replay Universe Expansion Plan

## Goal
Turn the deterministic black swan harness into a multi-universe replay framework that can:

- reproduce the same adversarial event stream bit-for-bit from a seed
- branch a system into multiple replay universes from the same base state
- measure divergence between kernel versions under identical pressure
- generate cryptographic attestations of survival, collapse, and recovery

## Core model

A replay universe is a deterministic tuple:

```text
U = (seed, epoch, event_index, kernel_hash, ledger_root)
```

Each universe must satisfy:
* same inputs => same event stream
* same seed => same black swan trace
* same trace => same verification outcomes
* different kernel hash => comparable but separate universe

### Replay branching
From a base state, the harness may fork into N universes:
* Universe A: baseline kernel
* Universe B: patched kernel
* Universe C: collapse-threshold variant
* Universe D: ledger-pressure variant

Each branch reuses the same deterministic event generator. The only changed variable is the kernel or policy under test.

### Deterministic event generation
Use a seed-derived hash function instead of RNG:
```rust
fn generate_event(seed: u64, epoch: u64, index: u64) -> Option<BlackSwanEvent> {
    let h = hash(seed ^ epoch ^ index);
    match h % 10_000 {
        0 => Some(BlackSwanEvent::LedgerForkCascade),
        1 => Some(BlackSwanEvent::ZkCollisionAttempt),
        2 => Some(BlackSwanEvent::FfiOverflowSpike),
        3 => Some(BlackSwanEvent::CollapseThresholdOscillation),
        4 => Some(BlackSwanEvent::ConcurrencySingularity),
        _ => None,
    }
}
```

No OS RNG, no time-based entropy, no thread jitter as a source of truth.

## Divergence metrics
Each replay universe must emit a comparable trace with:
- event count
- accepted/rejected transitions
- proof verification outcomes
- ledger commit count
- throttle activations
- collapse detections
- final root hash

Key metric:
```text
Divergence(Ua, Ub) = H(trace_a xor trace_b)
```

A higher score means the kernel reacted differently under the same pressure.

## Survival attestations
Each universe produces a signed report:
```json
{
  "seed": 42,
  "epoch": 7,
  "kernel_hash": "...",
  "ledger_root": "...",
  "events": 10000,
  "accepted": 9921,
  "rejected": 79,
  "collapse": false,
  "attestation": "..."
}
```

The report is valid only if:
- replay is reproducible
- the report hash matches the emitted trace
- the attestation key is bound to the runtime boundary

## Death criteria
A universe dies if any of the following happen:
- trace cannot be replayed from the same seed
- invalid proof is accepted
- ledger fork is accepted without deterministic rejection
- collapse detector fails to trigger under threshold breach
- two identical runs produce different outputs

## Integration points
- `cortex_rs`: truth plane, deterministic kernel, proof verification, ledger commit
- `cortex_chaos`: pressure plane, replay universe orchestrator, deterministic event stream
- `tests/adversarial.rs`: scenario assertions and death criteria

## Next implementation step
- add a replay state struct
- expose deterministic event generation in Rust
- add multi-universe runner
- serialize trace + attestation
- compare divergence across kernel versions
