<!-- [C5-REAL] Exergy-Maximized -->
# 🛡️ LandauerGuard (Ω₄) — Thermodynamic Context Compression

**Component:** `cortex/guards/landauer_guard.py`
**Status:** `ACTIVE` (Replaces HaikuGuard)
**Layer:** Admission Gate (SAGA-1)

## Epistemic Foundation (The Landauer Principle)
In autonomous C5-REAL systems, "elegance" is not aesthetic poetry (Haiku); it is the physical bounding of information entropy. Low-entropy data (conversational slop, repeated characters, meaningless filler) consumes energy without mutating the state matrix. The LandauerGuard enforces structural compression on all facts marked as `axiom` or `sacred`.

## Thermodynamic Constraints
To pass the LandauerGuard (Ω₄), a string must demonstrate high information density and strict size limits:

1. **Maximum Byte Size (< 256 bytes):** Axioms must be structurally compressed. Lengthy philosophical discourses are rejected as Entropy Drain.
2. **Minimum Shannon Entropy (> 3.5 bits/char):** The distribution of characters must be dense. "Green Theater" or padding strings fail this threshold.

## Causal Invocation
The guard is invoked during the `Write-Path Contract` within `FactManager._store_delegate`. Any violation instantly triggers a `GuardViolation`, logging the failure to the Master Ledger and aborting SAGA-1.

## Deprecation of HaikuGuard
The previous implementation, `HaikuGuard`, was deprecated because phonetic heuristics (counting syllables via vowels) introduced non-determinism into the consensus model (WBFT), violating the C5-REAL invariant that all structural gates must be deterministic.
