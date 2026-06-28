# CORTEX Cognitive System Manifesto
**Autor:** borjamoskv
**Nivel de Realidad:** #C5-REAL
**Anclaje Causal:** [`cortex/engine/core/ultrathink_physics.py`](../cortex/engine/core/ultrathink_physics.py)

---

## 1. El Colapso del Chatbot (La Ilusión del Chat)

La industria de consumo masivo sigue consumiendo anergía en el paradigma de la simulación conversacional:

```text
[Input Estocástico] → [Filtro de Contexto] → [LLM (C4-SIM)] → [Prosa Decorativa]
```

Este bucle carece de exergía computacional. El LLM opera en aislamiento termodinámico, sin capacidad de mutar físicamente su entorno ni preservar un ledger de su propia causalidad.

## 2. La Arquitectura del Sistema Cognitivo (C5-REAL)

El verdadero "Alpha" de la ingeniería agéntica en 2026 no reside en el tamaño del modelo, sino en la **infraestructura de contención y mutación causal** estructurada de la siguiente manera:

```text
                     ┌───────────────────────────┐
                     │     Orquestación (SAGA)   │
                     └─────────────┬─────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌───────────┐                ┌───────────┐                ┌───────────┐
│  Memoria  │                │ Guardas & │                │  Ledger   │
│  Causal   │                │ Taint     │                │ Inmutable │
└─────┬─────┘                └─────┬─────┘                └─────┬─────┘
      │                            │                            │
      ▼                            ▼                            ▼
[`cortex/memory`](../cortex/memory)            [`cortex/guards`](../cortex/guards)            [`cortex/audit`](../cortex/audit)
(SQLite WAL + Vec)          (ZK Seals & Taints)          (Cryptographic)
```

### Tabla de Equivalencias: Hype vs. Alpha

| Componente | Nivel C4-SIM (Hype/Youtubers) | Nivel C5-REAL (Sistemas Cognitivos / CORTEX) | Anclaje en `cortex/` |
| :--- | :--- | :--- | :--- |
| **Memoria** | RAG simple (coseno sobre trozos de texto) | Memoria Causal Episódica + Invariantes cristalizados. | [`cortex/memory`](../cortex/memory) / [`cortex/engine/crystallizer.py`](../cortex/engine/crystallizer.py) |
| **Herramientas** | Tool calling crudo y JSON ciego sin validación. | Contratos de Transición de Estado (Saga Pattern) con compensación atómica. | [`cortex/swarm`](../cortex/swarm) / [`cortex/tools`](../cortex/tools) |
| **Workflow** | Cadenas secuenciales (LangChain/AutoGPT). | Bifurcación asíncrona de agentes aislados (Swarm) con consenso BFT. | [`cortex/consensus`](../cortex/consensus) / [`cortex/agents`](../cortex/agents) |
| **Seguridad** | Prompts de sistema ("eres un asistente educado"). | Aislamiento a nivel de Tenant, Taint engine dinámico, ZK-Guards. | [`cortex/guards/sovereign_seals.py`](../cortex/guards/sovereign_seals.py) / [`cortex/crypto`](../cortex/crypto) |
| **Evaluación** | Feedback manual o "evaluación LLM" estocástica. | Verificación formal de aserciones en Ledger y hashes de estado. | [`cortex/audit/ledger.py`](../cortex/audit/ledger.py) / [`cortex/verification`](../cortex/verification) |

---

## 3. Física de la Exergía Cognitiva y Orquestación de Enjambres

### A. Ley del Isomorfismo Causal y Penalización Térmica (Landauer)

Un Sistema Cognitivo Real no asume una eficiencia lineal del Token. La computación incurre en fricción termodinámica por latencia y dispersión estocástica. Acorde a [`cortex/engine/core/ultrathink_physics.py`](../cortex/engine/core/ultrathink_physics.py), la verdadera exergía ($\Xi$) producida se modela como:

$$\Xi = \frac{O_{det} - E_{stoc}}{\Delta T \cdot (\lambda_L^{\Delta T})}$$

Donde:
- $O_{det}$: Output Determinista (Invariantes inyectados en Ledger/DB).
- $E_{stoc}$: Entropía Estocástica (Green Theater y tokens disipados).
- $\Delta T$: Tiempo de ejecución (Latencia).
- $\lambda_L$: Penalización térmica de Landauer (1.05).

Si el cociente exergético cae por debajo del Umbral de Singularidad, el sistema colapsa en "Anergía Conversacional" y aborta la mutación física (Rollback SAGA).

### B. Consenso Asimétrico y Topología LEGIØN-1

Las mutaciones P0 del sistema exigen un consenso que escala dinámicamente según el *Blast Radius* topológico:
- **Radio < 3:** Deep Think (Inferencia Simple).
- **Radio $\ge 5$:** Formación `TESTUDO` (15 agentes) — Defensa proactiva.
- **Radio $\ge 10$ + Exergía Crítica:** Formación `LEVIATHAN` (20-50 agentes) — Asedio de singularidad total con resolución BFT.

La meta de CORTEX es garantizar que ningún estado se modifique sin la matriz de validación termodinámica y el cuórum bizantino requeridos.
