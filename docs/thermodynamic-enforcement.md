<<<<<<< HEAD
# Thermodynamic Enforcement (Axiom Ω₁₃)

**Status:** Operational  
**Objective:** Encode physical and informational limits into system primitives to prevent unbounded stochastic drift and guarantee verifiable knowledge compaction.

This document freezes the operational contract of the Thermodynamic Enforcement suite. All changes to the modules listed here must strictly preserve these invariants. If tests fail against these properties, the system enters an uncontrolled entropic regime.

## 1. Causal Gap (Search / Indexing)
**Module:** `cortex.search.causal_gap`

**Inputs:**
- Target `CausalGap` (hypothesis, expected evidence, current confidence)
- Corpus of `SearchCandidate` objects (semantic score, evidence match logic)

**Outputs:**
- Ordered list of candidates ranked by `final_score`.

**Invariants & Ranges:**
- `semantic_score` ∈ `[0.0, 1.0]`
- `evidence_match_score` ∈ `[0.0, 1.0]`
- Return order must strictly be descending by `final_score`.
- **Property 1**: Exact evidence matches must monotonically increase (or stabilize) the score compared to purely semantic matches.
- **Property 2**: An empty corpus must immediately return an empty list without exceptions.

## 2. Epistemic Taint (Causality Graph)
**Module:** `cortex.engine.causality`

**Inputs:**
- Invalidated/Penalized `source_fact_id`
- Async causal graph state

**Outputs:**
- `TaintReport` containing affected count and discrete confidence downgrades.

**Invariants & Ranges:**
- Confidences follow the exact ordinal sequence: `["C5", "C4", "C3", "C2", "C1"]`.
- `new_confidence` ≤ `old_confidence` (Confidence floor is C1).
- **Property 1**: Taint introduced upstream MUST NEVER increase effective downstream trust.
- **Property 2**: The depth of the propagation (hops) monotonically increases the applied degradation penalty.
- **Property 3**: Invalidating a node with no descendants must yield an empty report safely.

## 3. Immune Metastability (Health & Stability)
**Module:** `cortex.immune.metastability`

**Inputs:**
- History of `SystemEvent`

**Outputs:**
- `MetastabilityReport` containing status (`healthy`, `dormant`, `metastable`, `chaotic`) and risk metrics.

**Invariants & Ranges:**
- `risk_score` ∈ `[0.0, 1.0]`
- `monoculture_ratio` ∈ `[0.0, 1.0]`
- **Property 1**: Idempotency — Equivalent input histories MUST produce identical deterministic outputs.
- **Property 2**: Non-decreasing Risk — Appending recent failures MUST NOT decrease the `risk_score`.
- **Property 3**: Monoculture Penalization — A higher similarity between event types strictly degrades the health status.

## 4. Shannon Exergy (Information Compaction)
**Module:** `cortex.shannon.exergy` and `cortex.shannon.analyzer`

**Inputs:**
- Abstract distributions of events/knowledge vs expected weights
- Empirical generation variables: tokens spent, compression ratio, noise fraction.

**Outputs:**
- `ExergyReport`, `exergy_score`, `exergy_ratio`, `dead_weight`

**Invariants & Ranges:**
- `exergy_score` ∈ `[0.0, 1.0]` (unless constrained exceptionally by noise offsets)
- `exergy_ratio` ∈ `[0.0, 1.0]`
- `dead_weight` ≥ `0.0`
- `tokens_spent` > `0` strictly.
- **Property 1**: Division Safety — Empty inputs or `0` token expenditure must fallback deterministically or raise explicitly.
- **Property 2**: Inverse Noise Correlation — Holding utility constant, increasing `noise_fraction` must monotonically decrease the final score.
- **Property 3**: Utility limits — Ornamental usage (high volume, low downstream utility) must strictly rank lower than compact utility.
=======
# THERMODYNAMIC-ENFORCEMENT.md

## 0. Regla Madre

Ningún axioma existe si no puede producir al menos una de estas consecuencias:
- `raise`
- `abort`
- `degrade_trust`
- `quarantine`
- `deny_write`
- `force_observation_cycle`

Si no hace una de esas seis cosas, es decoración.

---

## 1. Exergía Medible (`cortex/shannon/exergy.py`)

No basta con decir "medimos trabajo útil". Exergía significa que cada token consumido es pesado contra la reducción de incertidumbre que produce, mitigado por el riesgo irreversible de la acción.
- **Riesgo:** Clasificado como `read_only`, `memory_write`, `file_write`, `schema_mutation`, `destructive`.
- **Contrato Mecánico:** Todo agente estocástico que proponga un cambio de estado debe justificar su `ExergyResult`.
- **Efecto:** Si `ExergyResult.below_threshold == True`, se levanta `ThermodynamicWasteError` abortando el flujo de ejecución.

---

## 2. Decorative Mode (`cortex/guards/thermodynamic.py`)

El hipervisor detecta cuando un proceso o agente entra en estado de paseo y "generación ornamental":
- `tool_fails_without_new_hypothesis >= 3`
- `file_reads_without_ast_delta >= 5`
- `context_expansion_rate > uncertainty_reduction_rate`

**Efecto de entrar en modo `DECORATIVE`:**
- Solo lectura (0 writes concedidos).
- Se fuerza al sistema a volver al ciclo `[OBSERVE]`.
- Requiere nueva hipótesis explícita y disminución de contexto antes de reactivarse en modo `ACTIVE`.

---

## 3. Suntsitu Acotado (`cortex/immune/quarantine.py`)

Autonomía absoluta destructiva es inaceptable.
- Antes de una purga física, se calcula el **Blast Radius** (dependencias AST, imports cruzados, pruebas en el ledger).
- Si el módulo es crítico (ej. `criticality_score > 0.4`), no se demuele directamente, pasa a `QUARANTINE`.
- Purgas destructivas sin snapshots (`has_snapshot == False`) quedan tajantemente restringidas (`requires_snapshot = True`).
- **Efecto:** Prevención de demolición kamikaze autónoma y obligatoriedad de rollback precalculado.

---

## 4. Semantic Tombstones y Contaminación Causal (`cortex/engine/causality.py`)

El CORTEX Ledger no es ontología pura, es registro de decisiones. Cuando una hipótesis que se consideraba válida resulta ser errónea, la refutación **se propaga**.
- La confianza base decae (`decay` asintótico por profundidad en el DAG causal).
- El flag `tainted=True` enreda los nodos descendentes de la hipótesis refutada.
- **Efecto:** El sistema se aísla a fallar por "cascada de ruido", ya que se castiga y veta el uso de contexto que emane de nodos refutados para operaciones destructivas upstream.
>>>>>>> origin/main
