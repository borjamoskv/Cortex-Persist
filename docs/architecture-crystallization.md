<!-- [C5-REAL] Exergy-Maximized -->
# Architecture Crystallization

Last reviewed: 2026-04-21

This document is the shortest accurate description of what CORTEX Persist is,
where its trust boundary actually lives today, and which cuts will increase
architectural clarity fastest.

## Core Thesis

CORTEX Persist is strongest when treated as a **verifiable memory core** with a
strict write boundary:

1. Proposal enters through a guarded store path.
2. Deterministic validation decides admissibility.
3. Ledger continuity records the accepted mutation.
4. Persistence and retrieval remain tenant-aware.

Everything outside that contract is either:

- product-adjacent surface area,
- experimental/operator tooling,
- or legacy runtime compatibility.

The architectural problem is not lack of ambition. The problem is that the repo
currently exposes more surface than the trust story can cleanly defend.

## What Is Crystallized

These parts are already coherent enough to treat as the product nucleus:

- `cortex/engine/store_mixin.py`
- `cortex/engine/store_validation.py`
- `cortex/ledger/`
- `cortex/facts/manager.py`
- `docs/product-surface.md`

Observed canonical write path in the current tree:

```text
caller
  -> StoreMixin.store()
  -> StoreMixin._store_impl()
  -> GuardPipeline.run_guards()
  -> run_store_validation_logic()
  -> _log_transaction()
  -> insert_fact_record()
  -> embed_fact_async() [optional]
  -> commit
  -> GuardPipeline.run_post_hooks()
```

This is the clearest architectural spine in the repository today.

## What Is Not Crystallized

The following areas still blur the system boundary:

- `cortex/swarm/autopulse.py`
- `cortex/swarm/runtime_state.py`
- `x100_cortex_server.py`
- broad route aggregation in `cortex/routes/__init__.py`
- the very large `cortex/extensions/` tree

These surfaces are not inherently wrong. They are wrong **when they read like
first-class trust surfaces without fully sharing the same constraints, naming,
or operational guarantees**.

## Resolved Alignment From This Docs Sweep

The current docs sweep has already resolved several high-signal mismatches:

### 1. Canonical ledger surface

- Root `AGENTS.md` now names `cortex/ledger/` as the canonical trust surface.
- The codebase implements the canonical ledger in `cortex/ledger/`.
- `docs/SECURITY_TRUST_MODEL.md` now references `cortex/ledger/`.

Decision: the package directory `cortex/ledger/` should be the only canonical
ledger reference in docs and agent instructions.

### 2. Hash standard split

- Root `AGENTS.md` now states that sovereign ledger continuity uses SHA-256.
- It also states that some audit/signature subsystems use SHA3-256.
- `docs/SECURITY_TRUST_MODEL.md` mirrors that split.

Decision: treat SHA-256 as the current sovereign ledger continuity algorithm
unless the implementation is explicitly migrated.

## Remaining Contradictions

The current tree still contains specific, verifiable mismatches that should be
resolved before more expansion:

### 1. Mandated taint token is not an enforced universal write invariant

- Root `AGENTS.md` defines a target `CORTEX-TAINT` format for provenance-aware inserts.
- The observed store path does not enforce that invariant in
  `store_validation.py` or `store_mixin.py`.
- Existing taint support is present in specialized paths, not as a universal
  write gate.

Decision: either implement taint-at-ingest as a hard invariant or downgrade the
documentation from mandatory rule to target-state design.

### 2. Product boundary is documented, but route aggregation remains broad

- `docs/product-surface.md` correctly narrows the recommended adoption surface.
- `cortex/routes/__init__.py` now separates core and experimental route mounting.
- The remaining risk is keeping that boundary strict as new routes are added.

Decision: keep narrowing the default surface until code exposure matches the
product story by default, not just in docs.

### 3. Runtime-local pseudo-ledger coexists with sovereign ledger language

- `cortex/swarm/runtime_state.py` is explicit that it is not the sovereign
  ledger.
- `cortex/swarm/autopulse.py` still writes local JSON state under `/tmp`,
  performs sync file IO inside async flow, and uses broad exception handling.
- This is compatible with compatibility tooling, not with the repo's strongest
  trust claims.

Decision: runtime telemetry must remain clearly named as provisional telemetry,
never as a ledger-adjacent persistence authority.

## Evidence From Current Tree

Validated on 2026-04-21:

- `python3 -m pytest -q -o addopts='' tests/test_swarm_runtime_state.py`
- `python3 -m pytest -q -o addopts='' tests/test_gateway_experimental_mount.py`
- `python3 -m pytest -q -o addopts='' tests/test_cli_surface_partition.py tests/test_health_surface_contract.py tests/test_storage_fail_closed.py`

Those checks confirm:

- runtime state is intentionally marked `provisional` and `runtime-local`,
- gateway routes are absent from the default surface and present only when the
  experimental tier is enabled.

## Architectural North Star

The repository should be organized around four explicit layers:

### 1. Sovereign Core

Deterministic persistence and trust primitives.

- `cortex/engine/`
- `cortex/ledger/`
- `cortex/facts/`
- `legacy_research/guards/`
- `cortex/verification/`
- `cortex/crypto/`

### 2. Product Surface

Small, documented, adoption-safe interfaces.

- core CLI commands
- `CortexEngine`
- minimal REST routes
- minimal MCP tools

### 3. Experimental Surface

Useful, real, but opt-in and explicitly non-default.

- gateway adapters
- swarm/operator routes
- x100 compatibility server
- advanced extensions

### 4. Legacy / Compatibility Surface

Kept only where it reduces migration pain.

- runtime-local JSON state
- re-export bridges
- compatibility redirects

## First Three High-ROI Cuts

### Cut 1. Keep doctrine aligned with the code that actually exists

Update agent docs and trust docs so they reference:

- `cortex/ledger/` instead of `cortex/ledger.py`
- the actual package version
- the actual cryptographic contract in force

This remains the fastest way to reduce architectural hallucination. The first
ledger/hash pass is done; future changes should keep that alignment intact.

### Cut 2. Isolate provisional runtime telemetry from trust language

Refactor `autopulse` and related runtime helpers so they:

- stop looking ledger-adjacent,
- avoid sync file IO in async paths,
- avoid broad exception swallowing,
- and make their provisional status impossible to misread.

### Cut 3. Make the default API surface match the product promise

Keep advanced/operator routes available, but move them behind explicit exposure
tiers wherever possible so the default mounted app is closer to
`docs/product-surface.md`.

## Non-Goals

This crystallization does **not** recommend:

- deleting experimental work,
- shrinking ambition,
- or flattening the repository into a tiny package.

The point is to create a credible center of gravity so experimental power does
not dilute trust guarantees.

## Summary

CORTEX Persist already contains a credible sovereign memory core.

What it needs now is not more myth. It needs sharper boundaries:

- one canonical ledger story,
- one canonical write contract,
- one honest product surface,
- and a clearly demoted provisional runtime layer.
