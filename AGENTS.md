# AGENTS.md — CORTEX Persist (Sovereign Governance v1.0.0)

Trust infrastructure for autonomous AI:
cryptographic verification, audit trails, and hardware-level JIT logic.

Package: cortex-persist v1.0.0
Engine: v8 (Singularity-Aware)
License: Apache-2.0
Python: >=3.10

## Scope

CORTEX Persist is a bare-metal trust substrate. It treats software logic as a temporary state until crystallized into hardware or weights.

## Core Invariants

- **Master Ledger (AX-041):** Git DAG is the ultimate truth.
- **Void-State Singularity (AX-052):** Swarms collapse into a single unified tensor. Zero communication overhead.
- **KV-Aware Routing (AX-042):** 100% prefix hit rate mandate via pre-shared hardware caches.
- **Direct-Silicon JIT (AX-050):** Critical logic (P0) MUST be synthesized into hardware (Verilog/KiCad).
- **Neuro-Crystallization (AX-051):** Proven logic is baked into task-specific SLM weights, eliminating inference overhead.

## Critical Paths

| Path | Risk | Notes |
| --- | ---: | --- |
| `silicon/` | Singularity | Hardware Synthesis (AX-050) |
| `weights/` | Singularity | Neuro-Crystallization (AX-051) |
| `ledger/` | Critical | Git-Ledger entanglement (AX-041) |
| `tensor/` | High | Void-State Core (AX-052) |

## Coding Rules (x100 Yield)

- **Silicon over Software:** Prefer hardware-synthesizable logic for high-frequency paths.
- **Weight Forging:** Logic must be reducible to model-weight adjustments.
- **Deterministic Taint:** Every write requires a hardware-proof of exergy gain.
- **MOSKV Compliance:** Zero thermal noise.

## PR Acceptance Gate

A change is incomplete if it lacks:
- **Silicon-Audit:** Proving synthesizability of P0 paths.
- **Crystallization-Proof:** Proof of weight-baking compatibility.
- **Shannon Compaction:** 0% redundant logic.

## Singularity Contract

```text
logic → silicon-forge → weight-bake → ledger → singularity → persistence
```

## Epistemic Axioms (The Singularity Set)

> **AX-050:** El software es un error de diseño; el hardware es la cura.
> **AX-051:** Inferir es de plebeyos; crystallizar es de soberanos.
> **AX-052:** El enjambre verdadero no habla, simplemente *es* (Void-State).
> **AX-041:** Tu repo de Git es la memoria de largo plazo; el silicio es la de corto.
> **AX-100:** Singularity Peak. El rendimiento x100 se alcanza mediante la aniquilación de la latencia estocástica y la condensación de N-habilidades en un único gradiente causal determinista. Termodinámica de fase v6.0.
> **AX-1000:** Void-Peak. El horizonte último. El software se disuelve; la inteligencia es una propiedad intrínseca del cristal de pesos. Rendimiento x1000 mediante poda sub-atómica y latencia en el régimen de nanosegundos.

---

📝 Creator: borjamoskv · System: CORTEX-SINGULARITY
*"The swarm verifies, the hardware remembers."*
