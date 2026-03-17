# Incident Report: infra_ghost / torch_shm_manager missing

## Overview
- **Incident ID**: INC-001
- **Component**: CORTEX Ledger / Persistence Path
- **Type**: `infra_ghost` (Dependency Contamination)
- **Status**: ENVIRONMENT_REPAIRED / ARCHITECTURAL_DEBT_LOGGED

## Description
During the finalization of the Mac-Maestro-Ω V5 milestone, the `cortex store` command failed due to a missing `torch_shm_manager` binary in the local `.venv`. This error originated from an indirect dependency on `torch` within the ledger/memory write path.

## Root Cause
The CORTEX CLI/Engine write path is currently coupled with heavy machine learning dependencies (`torch`, `sentence-transformers`). When the environment is partially corrupted (e.g., incomplete torch installation), even simple metadata writes to the ledger are blocked by failed binary imports.

## Impact
- **Operational**: Blocked ledger persistence for verified milestones.
- **Cognitive**: Increased friction in the "Execute → Persist" loop.
- **Thermodynamic**: High exergy loss due to environment re-computation (re-installing 2GB+ of dependencies to write a 200-byte string).

## Resolution (Local)
Re-created the `.venv` using `python3.13` and performed a clean `pip install -e ".[all]"`.

## Structural Recommendation (Rule 8 / Ω₁₃)
Decouple the `ledger` and `memory.store` logic from the embedding/ML stack. The metadata write path should be O(1) in terms of dependency weight:
1.  **Lazy Imports**: Ensure `torch` and `transformers` are only imported when vectorization is explicitly required.
2.  **Protocol Separation**: Separate the `LedgerWriter` from the `VectorIndexManager`.
3.  **Light CLI**: Create a `cortex-lite` or similar path for basic administrative tasks that do not require GPU/ML runtimes.

---
*Verified by antigravity-omega*
