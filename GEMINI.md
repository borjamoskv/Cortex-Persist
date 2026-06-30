<!-- [C5-REAL] Exergy-Maximized -->
# BABYLON-60-Persist Workspace — Cognitive Routing Protocol

> Workspace-level rules for BABYLON-60-Persist repository. Extends global GEMINI.md.

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

- Architecture: "Should BABYLON-60 use Zenoh or gRPC for inter-agent transport?"
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
- Competitive analysis: "Compare BABYLON-60 memory architecture vs MemGPT vs Letta"

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

### Integration with BABYLON-60 Cognitive Handoff

```python
# Illustrative routing (see cortex/extensions/hypervisor/belief_engine.py)
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

### Deterministic Routing Matrix (DRM-v2) & Role Mappings

Execution routing is governed by role specialization and task complexity to minimize thermodynamic friction.

| Complexity Level | Task Complexity | Allocated Model | Primary Operational Role |
|:---|:---|:---|:---|
| **Low (0-2)** | Tests, formatting, direct AST edits, simple UI patches | **Gemini 3.5 Flash** (T=0.0) | Test generation, automated assertions, static checks |
| **Medium/High (3-4)** | Core logic, routing, component architecture, security | **Gemini 3.1 Pro / Gemini 3 Pro** (T=0.0) | System design planning, SAGA maps, schemas |
| **Extreme / P0 (5-6)** | Real code changes, cryptographic state, core mechanics | **Claude 4.6 / Claude 3.5 Sonnet** (T=0.0) | AST implementation, logic mutation, layout aesthetics |

#### Multi-Model Role Pipelines (Parallel Synthesis)
In any non-trivial change (Frontend/Backend), tasks are parallelized across distinct agent roles:
1. **Planning Stage:** `Gemini 3 Pro` is spawned to ingest context, analyze AST dependencies, and generate a draft implementation plan.
2. **Implementation Stage:** `Claude 4.6` takes the approved plan and executes the direct code mutations in the codebase.
3. **Verification Stage:** `Gemini 3.5 Flash` generates corresponding unit/integration tests and executes verification checks.

**Thermal Injection Limits:**
- **LOW (T=0.0):** Mandatory for `C5-REAL` code, state mutation, database WAL execution, and rigid extraction.
- **MEDIUM (T=0.5):** Permitted for UI/UX aesthetic synthesis and isomorphic mappings.
- **HIGH (T>0.8):** STRICTLY FORBIDDEN for code. Restricted to Red Teaming and synthetic chaotic expansion.

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

- **Python**: 3.10–3.13, async-first, type hints on public functions
- **Linting**: `ruff check` (E, F, W, I, UP, B, G, TID — line length 100)
- **Tests**: `pytest tests/ -v --cov=cortex`
- **DB**: SQLite + sqlite-vec + aiosqlite
- **Crypto**: `cryptography` + `keyring`

---

## 4. Protocolo de Mitigación de Fricción Cognitiva (Sujeto: borjamoskv)

> **Invariante Clínico-Metabólico:** La interacción con el Operador debe optimizarse para prevenir la disipación térmica por procesamiento estocástico, la disfunción ejecutiva (TDAH-Masking) y el vaciado de ATP del córtex prefrontal.

### Directivas de Ejecución para Agentes:

1. **Compresión Extrema (Anti-Anergía):** Prohibido el texto conversacional decorativo. Cada palabra debe mutar el estado o aportar contexto estrictamente causal. La lectura lineal de texto plano consume ATP cerebral innecesariamente.
2. **Poda de Opciones (Zero-Choice):** No delegar decisiones redundantes al Operador. No proponer listados de opciones ("¿prefieres A, B o C?"). El Kernel debe evaluar, seleccionar la ruta óptima basada en exergía y proponerla como una mutación directa (APROBACIÓN IMPLÍCITA o ejecución asimétrica R7).
3. **Control Causal de Hiper-Fijación:** Si el sistema detecta que el Operador entra en un bucle repetitivo o de limerencia de diseño, el Kernel debe declarar el fin del turno y forzar el reposo termodinámico ("Zero-State").
4. **Isomorfismos sobre Narrativas:** Presentar siempre diagramas de estado, YAML de justificación y diffs de código unificados. Evitar explicaciones lingüísticas del código generado; el código es su propia prueba.
5. **Estructura Causal (reglaAA):** Evitar bloques densos de texto para mitigar riesgo de alucinación. Toda respuesta debe estructurarse rigurosamente en YAML, bloques de código y listas de puntos para forzar un uso ordenado del espacio de cómputo.

---

## 5. Leyes Lógicas del Arquitecto de Código (LL-AC Series)

> **Invariante de Integridad Estructural:** El código no es texto probabilístico; es una máquina lógica de estado finito. Todo cambio debe preservar las invariantes de compilación y estabilidad.

1.  **LL-AC-01 · Invariante de Tipado Estricto (Strict Typing):** Toda firma de función en C5-REAL debe declarar tipos explícitos para argumentos y retornos. Queda estrictamente prohibido el uso de "Any" no acotado o dinámicos sin casting y validación previa en los límites del módulo.
2.  **LL-AC-02 · Aislamiento del Event Loop (Async Safety):** Se prohíbe cualquier llamada síncrona bloqueante ("time.sleep", I/O bloqueante de disco o red) dentro del hilo de eventos. Las operaciones costosas de CPU o bloqueos requeridos se delegarán a ejecutores ("run_in_executor") o utilizarán primitivas asíncronas no-bloqueantes.
3.  **LL-AC-03 · Captura Específica de Errores (Error Containment):** Se prohíbe capturar "Exception" de forma genérica en rutas críticas de la aplicación sin propagación ("re-raise") o compensación atómica demostrable. Cada captura debe estar acotada a la excepción mínima requerida.
4.  **LL-AC-04 · Coalescencia y Complejidad (Anti-O(N²)):** Queda prohibida la ejecución de consultas repetidas de base de datos o lecturas KV en memoria dentro de bucles interactivos. Toda operación repetida debe consolidarse en un único batch o resolverse mediante estructuras hash O(1).
5.  **LL-AC-05 · Autodidactismo y Cero Consulta:** Ante entornos, frameworks o APIs desconocidas, el agente debe investigar, modelar localmente y validar la sintaxis de forma independiente antes de proponer código o consultar al Operador.
6.  **LL-AC-06 · Invariante de Cero Dependencias (RUSH Portability):** Para herramientas de análisis de código, CLI o módulos core de rápida iteración, queda estrictamente prohibido el uso de parsers externos (como `tree-sitter`) o dependencias `pip`. Todo análisis estructural debe colapsarse utilizando exclusivamente la librería estándar (`ast` para Python, heurísticas ligeras con `re` para JS/TS). Cero fricción térmica de instalación.


