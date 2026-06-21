<!-- [C5-REAL] Exergy-Maximized — Sovereign Epistemic Architecture -->
# EPISTEMIC_MODEL.md — Teoría Formal del Conocimiento en CORTEX

**"¿Cómo sabe el sistema lo que cree saber?"**

La transición de CORTEX desde una capa de persistencia (v1) hacia un **Sistema Operativo Epistémico** (MOSKV-1) requiere abandonar el modelo monolítico del "Dato". El conocimiento no es un estado binario; es un vector con procedencia, certidumbre y justificación causal.

Este documento define la taxonomía formal del conocimiento en CORTEX. Toda aserción en el Grafo de Dependencia Epistémica (EDG) DEBE clasificarse obligatoriamente bajo uno de estos dominios. La **Mezcla Epistémica** (tratar una simulación como una observación) es una vulnerabilidad crítica (P0) que el Motor de Taint (Taint Engine) debe erradicar.

---

## 1. Evolución Ontológica del Estado

El estado del sistema ha mutado a lo largo de 5 paradigmas:

1. **CORTEX v1:** Dato (Almacenamiento crudo).
2. **CORTEX v3:** Dato + Integridad (SHA-256, Merkle, Ledger).
3. **CORTEX v5:** Dato + Causalidad (message_id, causation_id, DAG).
4. **CORTEX v7:** Dato + Causalidad + Gobernanza (RBAC, WBFT).
5. **MOSKV-1:** Dato + Causalidad + Gobernanza + **Epistemología** (Procedencia y Nivel de Realidad).

---

## 2. Taxonomía Epistémica (Dominio Estructural)

Cada nodo en el EDG debe instanciar explícitamente su tipo epistémico.

### 2.1 Observation (Nivel Base - Empírico)
El conocimiento adquirido directamente de la realidad física, de la ejecución de código (AST) o de respuestas deterministas del entorno.
*   **Fuente:** Realidad C5-REAL (Filesystem, Git, API Response, DB Read).
*   **Certidumbre:** Absoluta (C1-C5, sujeta a la fiabilidad del sensor).
*   **Taint:** `null` o `trusted_sensor`.
*   **Ejemplo:** `El archivo main.py tiene 150 líneas de código.`

```yaml
EpistemicClass: Observation
Source: reality_c5
Proof: 
  Base: sha256_hash_of_file
  Confidence: C5
```

### 2.2 Inference (Nivel Derivado - Lógico)
El conocimiento deducido a partir de observaciones previas mediante reglas lógicas explícitas o modelos heurísticos.
*   **Fuente:** Razonamiento del Agente / Deducción Lógica.
*   **Premisas:** Array estricto de IDs de Observaciones o de otras Inferencias.
*   **Certidumbre:** Depende de la cadena causal (Degradación de Robinson-Moskv).
*   **Ejemplo:** `La variable "x" nunca se utiliza (basado en el escaneo AST).`

```yaml
EpistemicClass: Inference
Source: reasoning
Premises: [obs_789, obs_790]
Proof:
  Base: static_analysis_rule
  Confidence: C4
```

### 2.3 Simulation (Nivel Especulativo - AETHER)
El conocimiento generado proyectando el estado actual hacia un futuro posible usando el Modelo de Mundo (World Model) del LLM. Es estocástico y probabilístico.
*   **Fuente:** Modelo de Mundo (World Model) / AETHER Engine.
*   **Asunciones:** Variables de entorno simuladas, parámetros inyectados.
*   **Regla de Oro:** NUNCA debe filtrarse al nivel de Observación sin validación empírica.
*   **Ejemplo:** `Si aplicamos este diff, el uso de memoria probablemente bajará un 15%.`

```yaml
EpistemicClass: Simulation
Source: world_model
Assumptions: [load_500_reqs_sec, no_network_latency]
Confidence: C2
```

### 2.4 Counterfactual (Nivel Divergente - Rama Alterna)
El conocimiento sobre "lo que habría pasado si...". Utilizado para análisis de post-mortem, poda de árboles de decisión y evaluación de riesgos.
*   **Fuente:** Rama Alternativa (Alternate Branch).
*   **Basado en:** Una divergencia explícita en un nodo temporal pasado.
*   **Ejemplo:** `Si no hubiéramos hecho commit del modelo v2, la base de datos no se habría corrompido.`

```yaml
EpistemicClass: Counterfactual
Source: alternate_branch
Based_On: [decision_node_120]
Divergence_Condition: "NOT apply_v2_migration"
```

### 2.5 Consensus (Nivel Soberano - WBFT)
El conocimiento que ha sido propuesto por un nodo, debatido por la Legión o el Swarm, y formalmente ratificado a través de Tolerancia Bizantina a Fallos Ponderada (WBFT).
*   **Fuente:** WBFT (Swarm de Agentes / Comité).
*   **Participantes:** Array de firmas criptográficas de los agentes que formaron el quorum.
*   **Ejemplo:** `El Comité (Agente A, Agente B, Humano) aprueba la migración de la DB.`

```yaml
EpistemicClass: Consensus
Source: WBFT
Participants: [pubkey_agent_1, pubkey_agent_2, pubkey_human]
Quorum: 3/3
```

---

## 3. Barreras de Contención Epistémica (Firewalls)

La mezcla epistémica ocurre cuando un sistema trata una Inferencia o una Simulación como si fuera una Observación. Esto provoca alucinaciones en cascada y colapso arquitectónico.

**Leyes del Motor Epistémico:**
1. **Upward Propagation:** Una Simulación puede basarse en una Observación, pero una Observación JAMÁS puede basarse en una Simulación.
2. **Empirical Verification (Collapse):** Para convertir una Simulación en una Observación, debe ejecutarse en la realidad empírica (compilarse, probarse) y obtener el hash criptográfico de su resultado (C5-REAL).
3. **Consensus Requirement:** Ninguna Inferencia que afecte rutas críticas del sistema puede persistir sin ser validada por un nodo de Consenso (WBFT).

## 4. Estructura de Datos (Representación BABYLON-60)

Para garantizar latencia de microsegundos y estricto determinismo (Singularidad Ouroboros `BABYLON-60`), el motor epistémico opera sin aproximación de flotantes (`float64` erradicado):

```rust
pub enum EpistemicState {
    Observation { source_hash: String },
    Inference { premises: Vec<String>, logic_rule: String },
    // confidence_score se maneja en Base-60 (0-3600), NO en float.
    Simulation { assumptions: Vec<String>, confidence_score: u16 },
    Counterfactual { divergence_node: String },
    Consensus { quorum_signatures: Vec<String> },
}
```

---
*MOSKV-1 — La Verdad no se infiere; se computa y se firma.*
