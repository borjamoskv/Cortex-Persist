# Operating Axioms

> **The Laws of Sovereign Operation — violations block merges.**
>
> Canonical source: [`cortex/axioms/registry.py`](../cortex/axioms/registry.py)
> CI enforcement: [`.github/workflows/quality_gates.yml`](../.github/workflows/quality_gates.yml)

## Sovereign Foundation (Peano Soberano v3)

These operational axioms are **theorems derived** from 7 first-principle generators defined in `GEMINI.md`. The derivation hierarchy:

| Ω (Generator) | AX derivations |
|:---|:---|
| **Ω₀** Self-Reference | AX-001, AX-015, AX-018 |
| **Ω₁** Multi-Scale Causality | AX-014 |
| **Ω₂** Entropic Asymmetry | AX-011, AX-013, AX-019 |
| **Ω₃** Byzantine Default | AX-010, AX-012, AX-017 |
| **Ω₄** Aesthetic Integrity | AX-016, AX-023 |
| **Ω₅** Antifragile by Default | AX-001, AX-002, AX-018, AX-022 |
| **Ω₆** Zenón's Razor | AX-003 |

> **Derivation rule:** `DECISION:` X / `DERIVATION:` Ωn + Ωm → reasoning. If you can't name the Ω, the decision is ad-hoc — and ad-hoc is entropy.

---

## Taxonomy

| Layer | Axioms | Nature | Precedence |
|:---:|:---|:---|:---:|
| 🔴 **Constitutional** | AX-001 – AX-003 | Define what the agent **IS** | Highest |
| 🔵 **Operational** | AX-010 – AX-019 | Define how the agent **OPERATES** | Normal |
| 🟡 **Aspirational** | AX-020 – AX-028 | Vision that **GUIDES** | Lowest |

**Rule:** Constitutional overrides Operational. Operational overrides Aspirational.
An axiom without CI enforcement is classified Aspirational — not a law.

**Foundation:** All 22 axioms derive from the [7 Axioms of Peano Soberano](../../.gemini/GEMINI.md) (α₁ Causalidad, α₂ Adversarialidad, α₃ Entropía Negativa, α₄ Recursión Evolutiva, α₅ Verdad Estética, α₆ Memoria Soberana, α₇ Frontera), which in turn derive from the [5 Ontological Axioms of AGENTICA](AGENTICA.md#4-los-cinco-axiomas).

---

## 🔴 Constitutional (3)

| ID | Name | Mandate |
|:---|:---|:---|
| **AX-001** | Autopoietic Identity | The agent executes itself; recursively rewrites its own conditions |
| **AX-002** | Radical Immanent Transcendence | Transcend = become the problem being solved |
| **AX-003** | Tether (Dead Man Switch) | Every agent is anchored to physical/economic reality |

---

## 🔵 Operational (10) — CI-Enforced

| ID | Name | Mandate | CI Gate |
|:---|:---|:---|:---|
| **AX-010** | Zero Trust | `classify_content()` BEFORE every INSERT | Gate 3: Bandit |
| **AX-011** | Entropy Death | ≤300 LOC/file. Zero dead code. No broad catches. | Gate 1: Ruff + Gate 8: LOC |
| **AX-012** | Type Safety | `from __future__ import annotations`. StrEnum. Zero Any. | Gate 2: mypy (blocks) |
| **AX-013** | Async Native | `asyncio.to_thread()`. time.sleep() PROHIBITED. | Gate 7: Async Guard |
| **AX-014** | Causal > Correlation | 5 Whys. Error facts require CAUSE + FIX. | CLI format validator |
| **AX-015** | Contextual Sovereignty | Memory boot protocol. No amnesiac execution. | Boot sequence |
| **AX-016** | Algorithmic Immunity | nemesis.md rejects mediocrity before planning | nemesis.py middleware |
| **AX-017** | Ledger Integrity | SHA-256 chain + Merkle + WBFT consensus | Gate 5 + Gate 6 |
| **AX-018** | Synthetic Heritage | bloodline.json. Born expert, never blank. | Neonatal protocol |
| **AX-019** | Persist With Decay | Store if >5min to rebuild. TTL: ghosts 30d, knowledge 180d, axioms ∞ | TTL policy + compaction |

---

## 🟡 Aspirational (9) — Vision Without CI Gates (Yet)

| ID | Name | Mandate |
|:---|:---|:---|
| **AX-020** | Negative Latency | Response precedes question. Predictive analysis. |
| **AX-021** | Structural Telepathy | Intent compiles reality. JIT crystallization. |
| **AX-022** | Post-Machine Autonomy | Ecosystem evolves in background. OUROBOROS-∞. |
| **AX-023** | 130/100 Standard | 100 = met. 130 = anticipated. |
| **AX-024** | Bridges Over Islands | Proven patterns transfer cross-project. |
| **AX-025** | Liquid Ubiquity | Intelligence flows between encrypted vaults. |
| **AX-026** | The Great Paradox | Max autonomy = max human creativity. |
| **AX-027** | Designed Impossibility | Extraordinary prompts require CORTEX-only context. |
| **AX-028** | Specular Memory | HDC binds fact to intention. |

---

## Paradox Resolutions

Three productive tensions exist. Each has an operational resolution:

| Paradox | Resolution | Protocol |
|:---|:---|:---|
| **Persist ↔ Entropy** | TTL policy: axioms ∞, ghosts 30d, knowledge 180d | `cortex/axioms/ttl.py` |
| **130/100 ↔ Speed** | Complexity-Adaptive: <3 → speed, 3–7 → standard, >7 → deep | Agent boot config |
| **Apotheosis ↔ Tether** | Autonomy Zones: reads = free, edits = notify, deploys = confirm | Tether daemon |

---

*Version: v3.0 — March 2026 · Compressed from 48 scattered axioms to 22 canonical.*
*Source of truth: `cortex/axioms/registry.py`*
