# VEX — Verifiable Execution for Autonomous Agents

> *"The only agent runner where you can prove, mathematically, that the agent did what it said it did."*

**Date:** 2026-03-02  
**Version:** 0.1.0-concept  
**Status:** Concept / Pre-Design  
**Author:** CORTEX Architecture Team  

---

## Executive Summary

VEX (Verifiable Execution) is a proposed extension to CORTEX that transforms it from a **trust infrastructure for agent memory** into a **trust infrastructure for agent execution**. VEX does not compete with LLM providers (inference). It competes in a category that does not yet exist: **cryptographically verifiable agent task execution**.

Every action an agent takes during VEX execution produces an **Execution Receipt** — a hash-chained, Merkle-anchored, consensus-scored proof that the agent did exactly what it claims to have done.

---

## The Problem

All existing agent runners (AutoGPT, CrewAI, OpenAI Operator, Gemini Code Assist) share a fundamental architectural flaw:

> **No runner can prove that the agent's execution history is untampered.**

| Runner | Memory | Execution Log | Integrity Proof | Consensus |
|:---|:---:|:---:|:---:|:---:|
| AutoGPT | Vector DB | JSON log | ❌ None | ❌ None |
| CrewAI | In-memory | stdout | ❌ None | ❌ None |
| OpenAI Operator | Ephemeral | API log | ❌ None | ❌ None |
| Gemini ADK | Context window | Session | ❌ None | ❌ None |
| **CORTEX VEX** | **L1+L2+L3 Tripartite** | **Hash-chained Ledger** | **✅ SHA-256 + Merkle** | **✅ WBFT** |

The implications for **regulated industries** (finance, healthcare, law, government) are stark:

- **EU AI Act Article 12**: AI systems must maintain audit trails and logging capabilities.
- **SOC 2 Type II**: Requires demonstrable evidence that controls operated effectively.
- **ISO 42001**: Demands traceability of AI decision-making processes.

No existing runner satisfies these requirements. CORTEX already does — for memory. VEX extends it to execution.

---

## What CORTEX Already Has (The 80%)

| Component | Module | Role in VEX |
|:---|:---|:---|
| **Hash-Chained Ledger** | `engine/ledger.py` | Every execution step is a transaction |
| **Merkle Tree Checkpoints** | `engine/ledger.py` | Batch verification of execution history |
| **WBFT Consensus** | `consensus/` | Multi-agent agreement on execution outcomes |
| **Tripartite Memory** | `memory/` | L1 (working) + L2 (vector) + L3 (episodic) |
| **Privacy Shield** | `api/gate/` | 11-pattern secret detection at ingress |
| **Self-Healing Daemon** | `daemon/` | 13 monitors for system integrity |
| **ApotheosisEngine** | `engine/apotheosis.py` | Entropy scanner + omniscience loop |
| **Sovereign Execution Loop** | `sovereign_agent_manifesto.md` | Conceptual: `run_sovereign_agent()` |
| **Bicameral Mind** | `sovereign_agent_manifesto.md` | Right Brain (reasoning) + Left Brain (execution) + Brainstem (safety) |
| **MCP Server** | `mcp/` | Model Context Protocol integration |
| **REST API** | `api/` | FastAPI with RBAC, rate limiting |
| **CLI** | `cli/` | 38 commands |
| **Circuit Breaker** | `proactive/circuit_breaker.py` | Failure isolation |
| **Compaction** | `compaction/` | Dedup + pruning |
| **OpenTelemetry** | `telemetry/` | Span tracing |

---

## What's Missing (The 20%)

### 1. Task Planner

A component that decomposes a high-level intent into a sequence of verifiable steps. Each step produces a `VerifiedStep` record in the ledger.

```python
@dataclass
class TaskPlan:
    """A decomposed task with verifiable steps."""
    task_id: str                    # Unique execution ID
    intent: str                     # Original human intent
    steps: list[PlannedStep]        # Ordered decomposition
    created_at: datetime
    plan_hash: str                  # SHA-256 of the plan itself

@dataclass
class PlannedStep:
    """A single planned step."""
    step_id: str
    description: str
    tool: str                       # Tool to invoke
    expected_outcome: str           # What constitutes success
    timeout_seconds: int
    tether_check: bool = True       # Verify against tether.md
```

### 2. Verified Execution Loop

The core loop that executes each step and produces hash-chained receipts.

```python
async def vex_execute(plan: TaskPlan) -> ExecutionReceipt:
    """Execute a plan with full cryptographic verification."""
    receipt = ExecutionReceipt(task_id=plan.task_id)
    
    for step in plan.steps:
        # 1. TETHER CHECK (Brainstem)
        if not await tether_allows(step):
            receipt.abort(reason="tether_violation", step=step)
            break
        
        # 2. EXECUTE (Left Brain)
        result = await execute_step(step)
        
        # 3. RECORD (Hash-chain)
        tx = await ledger.log_transaction(
            project=plan.task_id,
            action=f"vex_step:{step.step_id}",
            detail={
                "tool": step.tool,
                "input_hash": hash(step.input),
                "output_hash": hash(result.output),
                "duration_ms": result.duration_ms,
                "success": result.success,
            }
        )
        
        # 4. PERSIST MEMORY (L3)
        await cortex.store(
            project=plan.task_id,
            content=result.summary,
            fact_type="execution_step",
            meta={"tx_hash": tx.hash, "step_id": step.step_id}
        )
        
        receipt.add_step(step, result, tx)
    
    # 5. MERKLE CHECKPOINT
    receipt.merkle_root = await ledger.create_merkle_checkpoint()
    
    # 6. OPTIONAL: CONSENSUS (if multi-agent)
    if plan.requires_consensus:
        receipt.consensus = await consensus.request_votes(receipt)
    
    return receipt
```

### 3. Execution Receipt

The output artifact — a verifiable proof of execution.

```python
@dataclass
class ExecutionReceipt:
    """Cryptographic proof that an agent executed a task."""
    task_id: str
    plan_hash: str                  # Hash of the original plan
    steps: list[StepResult]         # Ordered results
    merkle_root: str                # Root of the Merkle tree covering this execution
    total_duration_ms: int
    status: str                     # "completed" | "aborted" | "partial"
    consensus_score: float          # WBFT consensus (1.0 = unanimous)
    receipt_hash: str               # SHA-256 of the entire receipt
    
    def verify(self) -> bool:
        """Self-verification: recompute receipt_hash and compare."""
        ...
    
    def export_proof(self) -> dict:
        """Export as a portable JSON proof for third-party verification."""
        ...
```

---

## Architecture: VEX in the CORTEX Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        VEX LAYER (NEW)                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Task Planner │  │  VEX Loop    │  │  Execution Receipt   │  │
│  │  (Decompose)  │  │  (Execute)   │  │  (Proof Generator)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         └─────────────────┴──────────────────────┘              │
│                            │                                    │
├────────────────────────────┼────────────────────────────────────┤
│                    CORTEX ENGINE (Existing)                     │
│                            │                                    │
│  ┌──────────┐  ┌──────────┴──────────┐  ┌──────────────────┐  │
│  │  Memory   │  │  Ledger (Hash-Chain) │  │  Consensus (WBFT)│  │
│  │  L1+L2+L3 │  │  + Merkle Trees      │  │  + Reputation    │  │
│  └──────────┘  └─────────────────────┘  └──────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │  Privacy  │  │  Daemon (13 monitors)│  │  Telemetry       │  │
│  │  Shield   │  │  Circuit Breaker     │  │  OpenTelemetry   │  │
│  └──────────┘  └─────────────────────┘  └──────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    INTERFACES (Existing)                        │
│  CLI (cortex run) │ REST API (/v1/vex/) │ MCP Server           │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Interface

```bash
# Execute a task with verifiable execution
cortex run "Refactor auth module to use HMAC-SHA256"

# Execute with specific LLM backend
cortex run --model gemini-2.5-pro "Fix the SQLite connection pool"

# View execution receipt
cortex vex receipt <task_id>

# Verify an execution receipt (third-party verification)
cortex vex verify <receipt.json>

# Export proof for compliance
cortex vex export <task_id> --format json --output proof.json

# List recent executions
cortex vex ls --limit 10
```

---

## API Interface

```
POST /v1/vex/run          — Submit a task for verified execution
GET  /v1/vex/{task_id}    — Get execution status + receipt
POST /v1/vex/verify       — Verify a receipt (third-party)
GET  /v1/vex/history      — List executions with filters
```

---

## Competitive Positioning

### What VEX Is NOT

- ❌ Not a new LLM (uses any LLM via configurable backend)
- ❌ Not a prompt engineering framework
- ❌ Not a RAG pipeline
- ❌ Not a chatbot builder

### What VEX IS

- ✅ The first agent runner with **cryptographic execution proofs**
- ✅ The only system where execution history is **tamper-evident via hash-chain**
- ✅ Built on **enterprise-grade trust infrastructure** (Merkle trees, WBFT consensus)
- ✅ **EU AI Act compliant** by default (Article 12 audit trails)
- ✅ Compatible with **any LLM backend** (Gemini, Claude, GPT, local models)

### Market Category

**Verifiable Agent Infrastructure** — CORTEX occupies the same structural position for AI agents that **Certificate Authorities** occupy for HTTPS, or that **Git** occupies for source code. Not the content. The trust layer around the content.

---

## One-Liner

> **VEX: The git for agent execution. Every action hash-chained. Every result provable. Every receipt verifiable.**

---

## Implementation Timeline

| Phase | Timeline | Deliverable |
|:---|:---|:---|
| **Phase 0** (current) | Week 1 | Concept doc (this document) + validation |
| **Phase 1** | Week 2-3 | `cortex/vex/planner.py` + `cortex/vex/loop.py` + `cortex/vex/receipt.py` |
| **Phase 2** | Week 4 | `cortex run` CLI command + basic tests |
| **Phase 3** | Week 5-6 | `/v1/vex/` API endpoints + third-party verification |
| **Phase 4** | Month 2+ | Multi-agent consensus on execution + external anchoring |

---

## Open Questions

1. **LLM Backend**: Should VEX be opinionated about which LLM to use, or provide a pluggable interface from day one?
2. **Step Granularity**: How fine-grained should steps be? (per-tool-call vs. per-subtask)
3. **Cost Model**: Should each VEX execution have a cost ceiling enforced by `tether.md`?
4. **External Anchoring**: When to introduce blockchain/timestamping anchoring for Merkle roots?
5. **Naming**: Is "VEX" the right name? Alternatives: CORTEX Execute, CORTEX Prove, CORTEX Audit.

---

## Axiom Derivation

```
DECISION: CORTEX Verifiable Execution (VEX) concept
DERIVATION: 
  Ω₀ (Self-Reference) — This document describes the next form of CORTEX; reading it executes it.
  Ω₂ (Entropic Asymmetry) — VEX reduces entropy: one system for both memory AND execution trust.
  Ω₃ (Byzantine Default) — No runner is trusted. VEX makes trust verifiable, not assumed.
  Ω₄ (Aesthetic Integrity) — A runner without proof is ugly = incomplete.
  Ω₆ (Zenón's Razor) — Conclusion hasn't mutated in 6 lenses. Time to document and build.
```

---

*Prepared for CORTEX Architecture Review | 2026-03-02*  
*Protocol: ULTRATHINK-INFINITE*  
*Standard: 130/100*
