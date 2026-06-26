# API Surfaces Architecture

**Status:** C5-REAL Structural Governance  
**Last Updated:** 2026-06-26

## Overview
This document explicitly resolves the architectural duality within the CORTEX-Persist repository. It defines the source of truth for the API surfaces, preventing operational uncertainty and divergent configuration drift.

---

## 🟢 Canonical API (Production)

* **Status:** Active / Supported (Canonical Source of Truth)
* **Module:** `cortex.api.core`
* **Alias:** `cortex.api:app` (via lazy `__getattr__` in `cortex/api/__init__.py`)

### Purpose
The official production surface of the CORTEX memory engine. It is the only API authorized to mutate core ledger state in production. All new features, bug fixes, auth mechanisms, and routes must be implemented here.

### Deployment & Execution
* **Local Dev:** `make serve` (invokes `uvicorn cortex.api.core:app`)
* **Docker/Cloud:** `Dockerfile` (invokes `uvicorn cortex.api:app`)
* **Security & Middlewares:** Full stack enforced deterministically (CORS via `CORTEX_ALLOWED_ORIGINS`, SecurityFraud, Tracing, Immune, RateLimit, Metrics, Metering, Auth).

---

## 🔴 Legacy Demo API (Removed)

* **Status:** Removed in v1.2.0
* **Module:** `api.server` (formerly at `api/server.py`)

### Purpose
Previously a prototype/demo surface originally built for the "Influencer Guard" concept. Completely removed in v1.2.0 to enforce the Canonical API and consolidate all execution within EventSovereigntyRuntime.

### Deployment & Lifecycle
* **Status:** Purged
* **Warning:** Do NOT attempt to use or resurrect this module.

---

## Governance Rules

1. **Single Source of Truth:** `cortex.api.core` is the absolute source of truth for the API contract.
2. **CORS and Configuration:** Environment-based configuration (like `ALLOWED_ORIGINS`) must be routed exclusively through `cortex.core.config` and consumed by the Canonical API.
3. **Deprecation Path:** Any useful components remaining in `api.server` (e.g., specific WebSockets) must be refactored as extensions or modular routers within `cortex.api` before `api.server` is ultimately purged.
