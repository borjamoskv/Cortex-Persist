# ADR 0004: Extension Tier Registry

## Status
Accepted

## Date
2026-06-29

## Context
CORTEX Persist contains 77 sub-modules under `cortex/extensions/`. This massive surface area created several architectural risks:
1. **Uncontrolled Imports:** Sub-modules could be imported implicitly or loaded at startup, increasing memory footprint and initialization times.
2. **Interpretive Ambiguity:** Experimental or speculative extensions (e.g., `dopamine_loop`, `wealth`, `cuatrida`) were structurally indistinguishable from core runtime extensions (e.g., `llm`, `swarm`, `mcp`).
3. **Byzantine Fault Risk:** Experimental code could execute in production or high-security environments, bypassing isolation boundaries.

To mitigate these risks under the C5-REAL execution kernel, we require a deterministic mechanism to classify, restrict, and audit extension loading.

## Decision
We implement a **three-tier Extension Registry** with dynamic import enforcement.

### 1. The Tiers
Every extension under `cortex.extensions.*` is classified into one of three tiers:
* **`CORE`:** Mission-critical modules (e.g., `llm`, `swarm`, `mcp`, `security`, `timing`, `git`, `platform`). Always allowed.
* **`OPTIONAL`:** Lazy-loaded and monitored modules (e.g., `browser`, `audio`, `compliance`, `fingerprint`, `signals`, `causality`). Allowed but subject to trace auditing.
* **`EXPERIMENTAL`:** High-risk, speculative modules (e.g., `dopamine_loop`, `wealth`, `bci`, `aether`, `cuatrida`). Blocked or strictly warned against unless explicit environment flags are set.

### 2. Governance Rules
1. **Dynamic Enforcement:** Any import under the `cortex.extensions.*` namespace is intercepted by a custom `importlib.abc.MetaPathFinder` (`ExtensionTierImportEnforcer`).
2. **Context Checking:** When an `EXPERIMENTAL` tier extension is imported, the enforcer checks if `CORTEX_EXPERIMENTAL_EXTENSIONS=1` is set.
3. **Execution Levels:**
   - Under standard execution: Prints a yellow diagnostic warning to `sys.stderr` and logs a warning.
   - Under strict mode (`CORTEX_STRICT_EXTENSIONS=1`): Immediately raises `ImportError`, blocking execution.
4. **Single Warning Constraint:** The registry caches warned extensions to prevent log flooding on nested sub-module imports.

### 3. Registry Mapping

| Extension | Tier | Loading Constraint |
|:---|:---|:---|
| `llm`, `swarm`, `mcp`, `security`, `timing`, `git`, `platform` | **CORE** | None |
| `browser`, `audio`, `compliance`, `signals`, `causality`, `songlines` | **OPTIONAL** | Monitored |
| `dopamine_loop`, `wealth`, `bci`, `aether`, `cuatrida`, `zkortex` | **EXPERIMENTAL** | Requires `CORTEX_EXPERIMENTAL_EXTENSIONS=1` |

## Consequences

### Positive
- **Guarantees cognitive isolation:** Prevents experimental or untrusted code from running implicitly in C5-REAL production contexts.
- **Reduces import overhead:** Establishes clear paths for lazy-loading non-core features.
- **Formalizes the codebase topology:** Developers must register new extensions in the registry mapping before importing them.

### Negative
- **Enforcement overhead:** Dynamic import hooks add a tiny microsecond latency to the initial import of extensions (mitigated after first load by standard `sys.modules` cache).

## Verification
1. Natively verified via `python3 -c "import cortex.extensions.aether"`, confirming diagnostic logging.
2. Verified that importing `CORE` or `OPTIONAL` extensions proceeds without warnings.
