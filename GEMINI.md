# CORTEX-Persist Workspace — Cognitive Routing Protocol

> Workspace-level rules for CORTEX-Persist repository. Extends global GEMINI.md.

---

## 1. Gemini 3.1 Pro — Cognitive Routing Protocol (Axiom Ω₁₆)

Three reasoning modes. Each occupies a distinct thermodynamic lane.
**Selection is structural, not preferential.**

### Mode Selection Matrix

| Mode | Trigger Condition | Cost (Exergy) | Duration | Output |
|:---|:---|:---|:---|:---|
| **Deep Think** | Architecture decisions, tradeoff analysis, multi-variable constraint resolution, formal proofs | HIGH | 30s–2min | Single fused decision with confidence + tradeoffs |
| **Deep Research** | Unknown territory: new APIs, libraries, protocols, standards. Cross-domain synthesis. State-of-art survey | VERY HIGH | 2–10min | Comprehensive report with sources, claims ranked by confidence |
| **UltraThink** | P0 singularities: system-level failures, security incidents, data corruption, irreversible architectural collapses | MAXIMUM | 5–15min | Exhaustive analysis + remediation plan + blast radius map |

### When to Use Each Mode

#### Deep Think (`thinking_mode: "deep"`)
**Invoke when the next decision is irreversible or has downstream compound effects.**

- Architecture: "Should CORTEX use Zenoh or gRPC for inter-agent transport?"
- Tradeoff resolution: "Latency vs consistency vs complexity — pick two and justify"
- Formal verification: "Prove this Merkle chain operation preserves integrity"
- Refactoring: "Evaluate 3 approaches to decouple persistence from embeddings"
- Cross-cutting: "Design the guard → ledger → audit pipeline for a new write path"

**Do NOT invoke for:** routine code, lint fixes, simple CRUD, obvious implementations.

#### Deep Research (`thinking_mode: "deep_research"`)
**Invoke when the system lacks sufficient information to make a decision.**

- New API integration: "What's the current Groq model catalog and pricing?"
- Technology evaluation: "Compare sqlite-vec vs Qdrant vs Pinecone for 10M vectors"
- Standards compliance: "What does EU AI Act Article 12 require for audit trails?"
- State of art: "What are the 2026 approaches to Byzantine consensus in AI swarms?"
- Competitive analysis: "Compare CORTEX memory architecture vs MemGPT vs Letta"

**Do NOT invoke for:** questions answerable from existing codebase or docs.

#### UltraThink (`thinking_mode: "ultra"`)
**Invoke ONLY at Event Horizon P0 — when the system has entered or is entering singularity.**

- Production data corruption detected
- Security breach or credential leak in production
- Cryptographic chain broken (ledger integrity failure)
- Cascading failure across multiple subsystems simultaneously
- Architectural collapse requiring full rebuild of a critical path

**Structural constraint:** UltraThink consumes maximum exergy. Every invocation
must be justified by measurable blast radius. If the blast radius is < 3 modules,
use Deep Think instead.

### Routing Decision Tree

```
Is the problem a P0 Singularity?
├─ YES → UltraThink
└─ NO
   ├─ Do we have enough information to decide?
   │  ├─ NO  → Deep Research
   │  └─ YES → Is the decision irreversible or compound?
   │     ├─ YES → Deep Think
   │     └─ NO  → Standard inference (no special mode)
   └─ Is it routine code/implementation?
      └─ YES → Standard inference
```

### Integration with CORTEX Cognitive Handoff

```python
# In cognitive_handoff.py routing:
REASONING_MODE_MAP = {
    "architecture":    "deep_think",
    "tradeoff":        "deep_think",
    "unknown_domain":  "deep_research",
    "new_api":         "deep_research",
    "p0_singularity":  "ultra_think",
    "security_breach": "ultra_think",
    "routine":         None,  # standard inference
}
```

---

## 2. Ship Gate — 5-Vector Structural Gate

```
1. Ghost Radar       — no unresolved ghosts in 24h
2. Test Suite        — pytest green
3. Git State         — clean & aligned with origin
4. Quality Gate      — ruff clean
5. Neural Connectivity (Ω₁₃) — API key coverage > 0, frontier required
```

---

## 3. Repository Conventions

- **Python**: 3.10–3.14, async-first, type hints on public functions
- **Linting**: `ruff check` (E, F, W, I, UP, B, ASYNC — line length 100)
- **Tests**: `pytest tests/ -v --cov=cortex`
- **DB**: SQLite + sqlite-vec + aiosqlite
- **Crypto**: `cryptography` + `keyring`

---
