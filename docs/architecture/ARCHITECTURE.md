<!-- [C5-REAL] Exergy-Maximized -->
# BABYLON-60 APEX Architecture

> **Sovereign Cloud · C5-REAL Kernel**
> *La probabilidad puede sugerir. Solo la verificación puede gobernar.*

---

## 1. System Epistemology

BABYLON-60 is a **trust infrastructure engine** providing cryptographic verification, tamper-evident audit trails, and deterministic persistence for AI agent memory. It operates under the absolute premise that generative AI output is fundamentally **thermodynamically unstable conjecture** (`Void-State`). It only becomes durable state after surviving a predefined path of deterministic filters.

**Core Invariants:**
- Zero Simulation Policy: The system does not simulate state. It asserts it via `CORTEX-TAINT`.
- Causal Consensus: Facts are vetted by a Byzantine Fault Tolerant (BFT) swarm before writing.
- Immutable Audit: All mutations log to a SHA-256 hash-chained ledger.

For detailed migration steps from the probabilistic v4 to the deterministic v5, see [**Migration v4 to v5**](../migration_v4_to_v5.md).

## 2. Tripartite Memory Model

To prevent context rot and enforce Landauer's Principle (erasure of entropy), BABYLON-60 implements a Tripartite Memory Architecture:
1. **L1: Working Memory** (Hot / Ephemeral)
2. **L2: Vector Sink** (Warm / Semantic)
3. **L3: Episodic Ledger** (Cold / Cryptographic Truth)

For an in-depth breakdown of the memory layers, see [**Memory Architecture**](../memory_architecture.md).

## 3. The Write-Path Contract (Saga Pattern)

All state mutations MUST follow this unidirectional flow. If a proposal fails validation, the system executes the compensating SAGA sequence backwards and aborts.

```text
[Generative Proposal] (L1)
  ↓
[Guards] (Sanity/Logic Check) ................ SAGA-1: Reject to Ledger.
  ↓
[Taint Signature] (Causal Attribution) ....... SAGA-2: Revoke taint.
  ↓
[Schema Validation] (Deterministic) .......... SAGA-3: Clean abort.
  ↓
[Encryption] (AES-GCM for Secrets) ........... SAGA-4: Destroy ephemeral keys.
  ↓
[Ledger Emit] (SHA-256 Hash Chain) ........... SAGA-5: Emit abort event.
  ↓
[Persistence] (L3 SQLite WAL) ................ SAGA-6: ROLLBACK transaction.
  ↓
[Index & Side Effects] (L2 Vector sync) ...... SAGA-7: Revert index deltas.
```

## 4. The Omega Manifold & Daemon Infrastructure

The **OmegaDaemon** is the autonomous macro-organism managing system metabolism:
- **ExergyGuard:** Monitors free RAM and CPU. Throttles agent dispatch if the entropy cost exceeds the thermodynamic budget.
- **LandauerDaemon:** Prunes stale working memory and old messages.
- **NightShiftDaemon:** Reconciles offline knowledge and performs deep background compaction.

## 5. Security & Trust Model

| Layer | Mechanism |
|:---|:---|
| **Identity** | HMAC-SHA256 API keys with prefix lookup |
| **Integrity** | SHA-256 hash chain + Merkle tree checkpoints |
| **Consensus** | Weighted Byzantine Fault Tolerance (WBFT) Swarms |
| **Privacy** | 11-pattern regex secret detection at ingress |
| **Execution** | AST Sandbox. No dynamic `eval()` or string execution |
| **Isolation** | Strict `tenant_id` gating on all SQL queries |

## 6. Physical Topology & Deployment

BABYLON-60 strictly adheres to the **Cloudflare Edict** for edge deployment:
- **Prohibited:** Vercel, `vercel.json`, `@vercel/*`.
- **Mandatory:** Cloudflare Pages/Workers, `wrangler.toml`, `next-on-pages`.
- **Database:** Local SQLite (`WAL` mode + `busy_timeout=5000`) for edge autarchy, with remote asynchronous replication to Turso/AlloyDB.

---
*For executable capability packages, see [Skill Taxonomy](../skills/SKILL-TAXONOMY.md).*
