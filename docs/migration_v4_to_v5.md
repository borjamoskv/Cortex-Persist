# [C5-REAL] Migration Guide: v4 to v5 (MOSKV-1 APEX)

The transition from v4 to v5 marks the paradigm shift from a probabilistic LLM wrapper to a **Sovereign C5-REAL Execution Kernel**. This migration is not a simple dependency bump; it requires architectural restructuring to comply with the new thermodynamic limits and epistemic boundaries of the system.

## 1. Epistemic Containment & C5-REAL Mandate

In v4, generative outputs could be directly returned or persisted.
In v5, **Generative Output is Conjecture**. 

- All state mutations must pass through deterministic guards (`cortex/guards/`).
- The Python execution is orchestrated via Rust bindings (`cortex_rs`) for direct mmap bypassing.
- You must declare your execution level (C5-REAL or C4-SIM). 

## 2. Infrastructure & Deployment (The Cloudflare Edict)

**CRITICAL:** Vercel ecosystems, `vercel.json`, and `@vercel/*` dependencies are strictly forbidden in v5 due to thermodynamic fracture and vendor lock-in entropy.

- **Frontend & Edge:** Must be deployed exclusively to Cloudflare Pages/Workers via `wrangler.toml` and `next-on-pages`.
- Any existing Vercel configuration must be purged before upgrading to v5.

## 3. Tripartite Memory (L1 / L2 / L3)

The legacy monolithic storage has been split:
- **L1 (Working Memory):** Redis or In-Memory dicts. Strictly for hot context.
- **L2 (Vector Sink):** `sqlite-vec` virtual tables (`cortex_embeddings_text`, `cortex_embeddings_visual`). Note: `vec0` tables do not support Foreign Keys. Synchronization must be manual and atomic.
- **L3 (Episodic Ledger):** SQLite WAL mode. The absolute cryptographic truth.

**Migration Action:** You must run the `cortex migrate v4-to-v5` command to split your monolithic database into the Tripartite structure.

## 4. The Omega Manifold & Daemon Substrate

Background tasks and agent coordination are no longer loose loops.
- All background workers must run inside the `OmegaDaemon` or specific Swarm Supervisors.
- **ExergyGuard** and **EntropySensor** now actively govern CPU/RAM usage. If an agent loops blindly, the daemon will trigger Apoptosis.
- Replace `asyncio.sleep()` in business logic with `QuorumGateway` consensus yields.

## 5. Strict SQLite Concurrency

Deadlocks are terminally forbidden.
- SQLite connections must enforce `busy_timeout=5000ms`.
- `WAL` mode is mandatory.
- The `transaction_mixin.py` enforces `BEGIN IMMEDIATE` to prevent read-modify-write race conditions.

## 6. Deprecations

- `argon2-cffi` has been removed. Use `cortex_rs::auth`.
- Legacy FTS tables are deprecated in favor of `sqlite-vec`.
- Broad `except Exception:` blocks are banned in critical paths. They must be narrowed to specific types.
