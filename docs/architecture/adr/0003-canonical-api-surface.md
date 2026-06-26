# ADR 0003: Canonical API Surface

## Status
Accepted

## Date
2026-06-26

## Context
CORTEX Persist evolved with two coexisting API surfaces:

1. **`cortex.api.core`** — The production API with full middleware stack (CORS, Auth, RateLimit, Metrics, Tracing, SecurityFraud, Immune, Metering), tenant isolation, and ledger integration.
2. **`api.server`** — A prototype/demo surface originally built for the "Influencer Guard" concept, toxicity tracking, and dummy telemetry WebSockets.

Both surfaces define their own `FastAPI()` instance. They do **not** share middlewares, authentication, security boundaries, or configuration. The coexistence created interpretive ambiguity: without explicit documentation, a developer encountering both modules had no reliable way to determine which was authoritative.

This ambiguity is the kind of problem that compounds silently. It doesn't cause immediate failures — it causes divergent implementations, inconsistent security postures, and wasted engineering effort over months.

## Decision
We establish `cortex.api.core` as the **single canonical API surface** for CORTEX Persist.

### Governance Rules

1. **Single Source of Truth:** `cortex.api.core` is the absolute source of truth for the API contract.
2. **CORS and Configuration:** Environment-based configuration (like `ALLOWED_ORIGINS`) must be routed exclusively through `cortex.core.config` and consumed by the Canonical API.
3. **Legacy Purged:** `api.server` has been completely purged from the codebase.
4. **Complete Removal:** The module and its prototypes are gone.
5. **Removal Executed:** `api.server` was fully removed in **v1.2.0**.
6. **Consolidation Path:** Completed. Any useful concepts were migrated to EventSovereigntyRuntime or dropped.

### Deployment Matrix

| Surface | Entrypoint | Status |
|:---|:---|:---|
| `cortex.api.core` | `uvicorn cortex.api.core:app` | ✅ Canonical |
| `cortex.api:app` | `uvicorn cortex.api:app` (lazy alias) | ✅ Canonical (alias) |
| `api.server:app` | `python api/server.py` | 🔴 Removed in v1.2.0 |

## Consequences

### Positive
- **Eliminates interpretive ambiguity.** The relationship between both surfaces is explicit and verifiable.
- **Provides objective basis for PR review.** Any change to `api.server` can be challenged against this ADR.
- **Establishes a removal timeline.** The deprecation is no longer implicit — it has a version target.
- **Machine-readable deprecation.** The `DeprecationWarning` makes the status visible in logs and CI.

### Negative
- **Migration burden.** Any downstream consumers of `api.server` must migrate before v1.2.0.
- **Documentation overhead.** This ADR must be maintained until the removal is complete.

## Verification
A governance test (`tests/architecture/test_api_governance.py`) enforces that `cortex.api.core` remains the declared canonical surface. This test will fail if:
- The canonical module is removed or renamed.
- The governance document is deleted.
- The deprecation warning in `api.server` is removed.
