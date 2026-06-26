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

## 🔴 Legacy Demo API (Deprecated)

* **Status:** Deprecated
* **Module:** `api.server` (located at `api/server.py`)
* **Entrypoint:** `api.server:app`

### Purpose
A prototype/demo surface originally built for the "Influencer Guard" concept, toxicity tracking, and dummy telemetry WebSockets. It is a completely separate FastAPI application that **does not share** the `app` instance, middlewares, or security boundaries of the Canonical API.

### Deployment & Lifecycle
* **Direct Execution:** `python api/server.py`
* **Lifecycle:** Pending consolidation or removal. It is retained solely for historical reference of the Influencer Guard concept.
* **Warning:** Do NOT use this module as a reference for new feature development. Do NOT implement fixes here unless they are specific to the legacy demo flow.

---

## Governance Rules

1. **Single Source of Truth:** `cortex.api.core` is the absolute source of truth for the API contract.
2. **CORS and Configuration:** Environment-based configuration (like `ALLOWED_ORIGINS`) must be routed exclusively through `cortex.core.config` and consumed by the Canonical API.
3. **Deprecation Path:** Any useful components remaining in `api.server` (e.g., specific WebSockets) must be refactored as extensions or modular routers within `cortex.api` before `api.server` is ultimately purged.
