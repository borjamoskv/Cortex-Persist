# Deterministic Replay Universe Spec

## Goal
Expand the adversarial model from a single deterministic black swan stream into a family of replayable universes.

Each universe is a fully deterministic branch of the same seed space. No OS RNG, no hidden entropy, no nondeterministic timing as a source of truth.

## Core idea
A universe is identified by:

- `universe_id`
- `seed`
- `epoch`
- `branch_index`
- `kernel_hash`
- `ledger_root`

A replay is valid only if the same tuple reproduces the same trace bit-for-bit.

## Universe model
```text
Universe = (seed, epoch, branch_index, kernel_hash)
```

The replay engine emits an ordered sequence of adversarial events:

```text
trace = f(seed, epoch, branch_index, event_index)
```

No event may depend on wall-clock time, OS jitter, or ambient entropy.

## Branching rules
Branching happens only when a deterministic condition is met:

- state hash crosses a threshold
- ledger fork pressure exceeds a bound
- proof verification produces a stable reject path
- collapse detector enters a boundary band

The branch index is derived from the trace, not from randomness:

```text
branch_index_next = H(trace || state_hash || event_index) mod N
```

## Replay invariants
1. Same inputs produce the same universe.
2. Same universe produces the same trace.
3. Same trace produces the same ledger deltas.
4. No universe may mutate production state.
5. All universes must be replayable on demand.

## Harness surface
The replay harness must expose:

- `spawn_universe(seed, epoch, branch_index)`
- `step_universe(universe)`
- `snapshot_universe(universe)`
- `replay_universe(snapshot)`
- `compare_traces(a, b)`

## Death criteria
A universe is invalid if:

- a replay diverges from its original trace
- a branch is not reproducible
- a proof verifies in one branch but not another with identical inputs
- a ledger commit appears in a branch that should have been rejected
- the collapse detector fires inconsistently across replays

## Acceptance criteria
The system is valid only if:

- all deterministic branches are reproducible
- all divergence points are explainable by the branching function
- trace comparison returns identical outputs for identical inputs
- production state remains untouched

## Suggested next implementation step
Add a Rust module that implements:

- `ReplayUniverse`
- `UniverseSnapshot`
- `DeterministicBrancher`
- `TraceComparator`

and wire it behind a test-only feature flag.
