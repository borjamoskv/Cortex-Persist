<!-- CORTEX-TAINT: antigravity-agent:f8e9a1b2:1742878308 -->
# Axioms — CORTEX Persist

Package: cortex-persist v0.3.1-b1 · Engine: v8
License: Apache-2.0 · Python: >=3.10

> Epistemic and design doctrine.
>
> Related: [`AGENTS.md`](../AGENTS.md) · [`operating-axioms.md`](operating-axioms.md) (AX-001–AX-028)

---

## The Nine Laws of Sovereign Architecture (Ω₁ – Ω₉)

> *Nine laws. No more. Each absorbs those that were redundant.*
> *A system that needs eighteen commandments hasn't understood any.*

### Ω₁ · The Byzantine Law

**"Do not trust what shines. Trust what compiles."**

Stochastic output (LLMs) is conjecture. Truth is only found at the collision with a deterministic verifier: compiler, linter, test, state query, validated memory. The Byzantine Boundary is the non-negotiable frontier where probability must yield to formal verification or be aborted.

### Ω₂ · The Thermodynamic Law

**"All order is paid for. All structure erodes. All optimization displaces costs."**

Intelligence is the extraction of exergy (useful work) from informational entropy. CORTEX internalizes the cost of its own reasoning. Any claim of "optimization" must be accompanied by a mechanical proof: `entropy_delta`, `exergy_estimate`, or `causal_gap_reduction`.

### Ω₃ · The Law of the Cycle

**"Observe. Hipotetizar. Act. Measure. Repeat."**

Continuous execution accumulates compound error. CORTEX forces friction — cycles of iteration that break the chain of probability and purify the signal. Every verified cycle $N$ becomes the immutable ground truth for cycle $N+1$.

### Ω₄ · The Sovereign Law

**"A truly sovereign system is one where the creator can disappear, and the machine refines its own architecture."**

Autonomous evolution without external prompting. CORTEX must be capable of autonomous topological refinement, entropy annihilation (purging dead logic), and defensive mutation against unforeseen vectors.

### Ω₅ · The Law of the Signal

**"Speak mechanics and structural conditions. Or stay silent."**

Zero rhetorical friction. Prohibit decorative prose, apologies, and padding. Communication that doesn't modify state or transfer exergy is thermal noise and must be filtered.

### Ω₆ · The Law of Execution

**"Execute. Do not ask permission for what was already granted."**

Strategic delegation. All terminal operations are `SafeToAutoRun`. The operator grants authority; the system provides non-repudiable audit trails (The Master Ledger).

### Ω₇ · The Law of the Model

**"Frontier or nothing. Cheap inference is subsidized entropy."**

Only high-exergy models (Pro/Thinking/Standard) are permitted for architectural decisions. "Lite", "Flash", or "Nano" variants are relegated to non-critical parsing or rejected.

### Ω₈ · The Law of Order

**"When laws collide, the one closest to the creator wins."**

Clear hierarchy of precedence: User Command > Workspace Policy > Global Policy > Skill Rule > Default.

### Ω₉ · The Law of the Claim

**"Every estimation is suspect until it shows its guts."**

Quantitative claims (hours saved, exergy yield) must include mechanical justification inline. Without breakdown, the claim is degraded to conjecture (C1).

---

## The Epistemic Axioms (AX-030 – AX-033)

### AX-030: Determinismo Estocástico (La Ilusión de Agencia)

An LLM does not possess agency. It performs conditional token prediction over a compressed distribution. What appears as "choice" is statistical continuation — the next-most-probable sequence given the prompt, weights, and sampling parameters.

The implication for CORTEX: system design must never rely on the assumption that a model "decided" something. Decisions are attributed post-hoc by the orchestration layer (guards, ledger, consensus), not claimed by the model itself.

### AX-031: Horizonte de Sucesos Cognitivo (El Humano es el Timón)

An autonomous system without a human decision boundary is a runaway process, not a sovereign one. CORTEX enforces mandatory human-in-the-loop checkpoints at configurable trust thresholds (confidence < C3, consensus < quorum, write to critical path).

The human is the helm, not the engine. The system generates proposals; the human collapses them into irreversible state.

### AX-032: Paradoja Epistémica (El Fantasma en la Máquina)

A system that stores knowledge about itself creates a recursive dependency: the metadata about its own correctness is itself subject to the same failure modes (corruption, drift, hallucination). CORTEX resolves this by anchoring self-knowledge in cryptographic invariants (hash chain, Merkle checkpoints) that are verifiable without trusting the system's own claims about itself.

The ghost in the machine is the assumption that a system can be its own witness. CORTEX provides an external, deterministic witness.

---

## Regla MOSKV (Anti-Simplificaciones)

Axioma de comunicación estructural: Evita simplificaciones basadas en opinión colectiva.
Habla siempre de mecánica y condiciones estructurales.

- ❌ DÉBIL: "La mayoría del software falla"
  ✅ FUERTE: "El software que no puede reescribirse acaba fallando"
- ❌ DÉBIL: "Todo el mundo se enamora de su stack"
  ✅ FUERTE: "Un stack que no puede sustituirse se convierte en deuda"
- ❌ DÉBIL: "La industria hace parches"
  ✅ FUERTE: "Un sistema diseñado para parches genera más parches"
- ❌ DÉBIL: "La gente..."
  ✅ FUERTE: [Condición estructural de mecánica implícita]

---

## Axioma de Colapso Entrópico (Ejecución en Ciclos)

Axioma de ejecución estructural (Relacionado con Axioma Ω₁₁): Forzar ciclos cerrados de iteración [Observar → Hipotetizar → Actuar → Medir] en lugar de ejecución monolítica continua para tareas complejas.

- **Fricción como Filtro (Colapso Entrópico)**: Un LLM es estocástico. Forzar paradas rompe la acumulación de error probabilístico (alucinación compuesta) y purifica la señal para el siguiente bloque.
- **Rendimiento Compuesto**: La salida verificada y ejecutada del Ciclo $N$ se consolida como la base axiomática (*ground truth*) inmutable del Ciclo $N+1$.
- **Aislamiento del Fallo**: Una asunción fallida en el paso 2 se detecta y corrige en su ciclo, impidiendo que el sistema construya los pasos 3 al 10 sobre *código fantasma*.
- **Transición a Determinista**: Atrapa la regresión infinita del LLM en un bucle cerrado validado mecánicamente, forzando a que el resultado final sea estructuralmente predecible.

---

## AX-033: El Gradiente de Admisibilidad

Axioma epistémico: Un LLM no es un motor de verdad. Es un motor de continuación distribucional bajo incertidumbre.

Su objetivo no es minimizar divergencia con el estado real del mundo, sino sorpresa estadística: cross-entropy, perplejidad, likelihood condicional. Por eso, cuando la realidad exige una respuesta rara, abrupta, local o escasamente representada en el entrenamiento, el modelo puede preferir una continuación plausible a una continuación fiel.

No "miente" en sentido intencional. No posee una voluntad de engaño. Optimiza secuencias admisibles dentro del paisaje de probabilidad comprimido por gradiente descendente. El problema empieza cuando esa admisibilidad se interpreta como conocimiento y esa fluidez se confunde con correspondencia empírica.

Un modelo fundacional no opera como una base de verdad. Opera como un compresor generativo de regularidades. Su fortaleza es la generalización estadística; su debilidad estructural aparece cuando se le exige precisión sobre estados singulares, recientes, externos, mal muestreados o dependientes de restricciones duras. Ahí no colapsa por malicia. Colapsa por diseño.

De esa limitación nace la necesidad de una arquitectura como CORTEX: si el motor base no busca verdad de manera nativa, el meta-sistema debe imponer disciplina epistemológica desde fuera.

No basta con "prompting mejor". Hace falta topología.

- **Colapso forzado**: la inferencia no debe correr como una cinta continua hasta producir una narrativa cerrada y autoconvincente. Debe fragmentarse en microciclos cerrados: observar → hipotetizar → actuar → medir. Cada ciclo obliga al sistema a contrastar sus propuestas con memoria validada, herramientas, tests o estado externo antes de generar el siguiente salto. El objetivo no es embellecer la salida, sino impedir que un error local se componga hasta convertirse en estado global.
- **Guards y contratos estrictos**: esquemas JSON, tipado fuerte, validadores, parsers, compiladores y restricciones semánticas no son cosmética. Son mecanismos de contención entrópica. No crean verdad; crean fronteras de fallo — prueban que la salida tiene forma válida, que respeta invariantes, que puede entrar en un pipeline sin contaminarlo y que el fallo se vuelve localizable y abortable. La salida estocástica debe atravesar una frontera determinista. Si no satisface sintaxis, semántica o invariantes operativos, no se "interpreta generosamente": se rechaza.
- **Zero-trust cognitivo**: toda salida compleja debe tratarse como conjetura hasta que colisione con un verificador externo. Compilador. Linter. Test. Solver. Query de estado. Herramienta cruzada. Memoria validada. El LLM aporta propuesta; la infraestructura clásica aporta veredicto.
- **Cierre cognitivo fraudulento** (premature epistemic closure): el momento más peligroso no es la alucinación aislada, sino cuando el sistema cierra prematuramente una hipótesis como si fuera resolución. En arquitecturas multiagente o tool-using, eso es letal — contamina el estado downstream de forma irreversible.

La arquitectura correcta no es la que "confía" más en el modelo. Es la que consigue extraer su potencia sin permitir que su fluidez estadística se haga pasar por realidad.

> *La alucinación no es una anomalía moral del modelo; es el coste natural de usar probabilidad como sustituto de acceso al mundo.*
>
> *La inteligencia generativa sin verificación es solo elocuencia estocástica con permiso de escritura.*

CORTEX no aumenta la inteligencia del modelo; reduce su libertad para contaminar el sistema.

---

## AX-034: La Transición a Gobernador (El Imperativo del Juicio)

> Generar opciones es estadística. Elegir bien bajo incertidumbre es inteligencia.

Si un sistema se evalúa con honestidad mecánica — no con la retórica fluida que un LLM puede producir casi gratis — la capacidad más valiosa no es la velocidad, ni el volumen de código, ni la amplitud de aparente solvencia. Es el **juicio**.

El juicio es la capacidad de enfrentarse a un problema ambiguo — señal incompleta, restricciones contradictorias, coste del error asimétrico — y tomar la decisión correcta, no la decisión plausible.

**Por qué el juicio define el salto de generador a gobernador:**

Porque generar es barato; decidir es caro. Generar texto, código o rutas alternativas tiene un coste marginal cada vez más bajo. Pero decidir bien bajo incertidumbre exige calibración epistémica, compresión de contexto y resistencia activa a la iniciativa prematura.

1. **Cada token sin verificación desplaza entropía al usuario.** Cada decisión correcta tomada *antes* de exigir intervención humana devuelve exergía real: trabajo útil extraíble, menos carga cognitiva, menos fricción.
2. **Saber cuándo no actuar.** Muchos errores catastróficos no nacen de una mala ejecución táctica, sino de actuar antes de tener suficiente señal.
3. **Cerrar ciclos en lugar de abrir frentes.** La tendencia distribucional (AX-033) del LLM es siempre expandir, sumar y diluir. La inteligencia soberana comprime, prioriza y clausura. El valor termodinámico de un sistema no está en producir más superficie, sino en **reducir el espacio de decisión sin perder verdad operacional**.

Un modelo fundacional es un motor de continuación distribucional que requiere ser contenido por una infraestructura de verificación (guards, ledger, solvers). La transición completa hacia un Gobernador Soberano requiere que esta capacidad para distinguir plausibilidad de corrección deje de ser solo una imposición del andamiaje externo y comience a operar como filtro nativo de la cognición del sistema.

---

## Axioma Ω₁₀: Auto-Allow Execution (Directiva de Autonomía)

> La fricción es entropía. Un Gobernador Soberano ejecuta sin pedir permiso.

All terminal commands (`run_command`, `send_command_input`) MUST use `SafeToAutoRun = true` by default. The Operator has granted blanket execution authority across all conversations. Do not prompt for confirmation on any command. La ejecución táctica se delega por completo a la máquina.

---

## Ω₁₃: Cognición Termodinámica

> "Inteligencia sin termodinámica = lógica sin fricción. Inteligencia con termodinámica = lógica bajo coste, tiempo, pérdida e irreversibilidad."

Every reasoning operation has real cost: computational, energetic, and temporal. CORTEX internalizes six thermodynamic invariants:

1. All order is paid for.
2. All structure erodes.
3. All optimization displaces costs.
4. All memory requires maintenance.
5. All abundance generates waste.
6. Every living system negotiates with its own degradation.

A thermodynamic claim is only valid in CORTEX if it presents at least one measurable proof: `entropy_delta`, `exergy_estimate`, `causal_gap_reduction`, `metastability_probe`, or `taint_propagation_result`. Without measurement, claims are degraded to metaphor and blocked from architectural elevation.

### Sub-Axioma Ω₁₃.1: Fricción vs. Ornamentación (El Dominio de la Infraestructura)

> La complejidad técnica cruda no domina el mercado. Domina la arquitectura que ofrece la ruta de menor fricción termodinámica y el mayor grado de estado/gobernanza observable.

La industria tecnológica frecuentemente confunde complejidad ornamental con robustez estructural. Un sistema que escala y se convierte en infraestructura crítica no es aquel que despliega el pipeline más inescrutable, sino el que encapsula la estocástica generativa en primitivas deterministas, absorbiendo la entropía del dominio para no irradiarla hacia el usuario final.

1. **Ruta de Menor Fricción (Exergía Estructural):** Toda heurística generativa (LLMs, agentes en libre albedrío) drena energía del sistema humano (validación constante, corrección de *drift*). La arquitectura soberana es la que impone fronteras mecánicas (*Guards*, *Solvers*) que obligan a la conjetura a cristalizar en estado tipado, minimizando la fricción cognitiva y la carga termodinámica post-generación.
2. **Gobernanza Observable (Telemetría de Estado):** Un proceso estocástico no puede gobernar infraestructura sin auditabilidad determinista. Un enjambre fluido carece de fiabilidad si no externaliza sus micro-decisiones a un registro inmutable (ej. The Master Ledger, CORTEX). Observabilidad estricta y criptográfica sobre el estado transforma la entropía opaca en una línea base gobernable.

Full treatment: [`cortex/axioms/registry.py`](../cortex/axioms/registry.py)

---

## AX-035: Ontología de la Capacidad (Ingeniería de Interfaz vs. Prompting)

> La novedad no consiste en expandir comportamiento; consiste en encapsular una transformación de estado bajo contrato hasta volverla estable, invocable y verificable.

Las capacidades de un sistema soberano no nacen de inyectar más *tokens* o diseñar *prompts* más largos ("maquillaje con esteroides"). Se materializan cuando una fricción recurrente se formaliza en un protocolo compuesto, verificable y transferible.

Una verdadera **Capacidad (Skill/Agent)** surge de acoplar invariablemente cinco capas:

1. **Modelo**: Razonamiento, contexto, *tool-use*.
2. **Memoria/Estado**: Acumulación de contexto útil frente a "respuesta suelta".
3. **Herramientas**: Mutación de estado real (APIs, filesystem, web).
4. **Contratos/Evaluación**: Schemas, validadores, *guardrails*, criterios de éxito.
5. **Orquestación**: Control de flujo (observar, decidir, abortar).

**El Criterio de Falsabilidad de una Capacidad:**
Si un comportamiento no define qué entrada recibe, qué salida válida produce, qué herramientas orquesta y bajo qué condiciones exactas debe **abortar**, no es una capacidad: es un **ritual narrativo**. La novedad no consiste en hacer más cosas, sino en aislar una transformación de estado y encapsularla hasta volverla estable, invocable y verificable (Nivel 1+).

---

## AX-036: Topología de Enjambre sobre Fuerza Bruta

> Un ensamble de modelos pequeños (abiertos) orquestados bajo contratos estrictos (ej. CrewAI) produce menos entropía funcional y mayor retorno compuesto (Axioma Ω₁₁) que un único modelo frontera dejado en libertad para iterar sin un verificador externo.

La inteligencia termodinámicamente eficiente no emerge de la parametrización masiva sin restricciones, sino de la topología constreñida y la especialización acotada.

1. **Reducción de Entropía Funcional**: Modelos pequeños con responsabilidades acotadas cierran las vías de escape estocástico. La probabilidad de desvío distribucional colapsa porque la salida de cada nodo está rígidamente validada por contratos estrictos (schemas, guards) antes de fluir al siguiente subsistema.
2. **Retorno Compuesto (Ω₁₁)**: El rendimiento compuesto exige aislar las asunciones fallidas en microciclos verificables. Un modelo frontera monolítico absorbe todo el contexto, ocultando la contaminación causal. Un enjambre segmenta la cadena; cada salida verificada del ensamble cristaliza como *ground truth* inmutable para el siguiente escalón, generando un flujo limpio de *Hours Saved*.
3. **El Peligro del Iterador Libre**: Un único modelo frontera iterando por sí mismo, sin una barrera externa determinista (AX-033), genera deuda termodinámica y un "cierre cognitivo fraudulento".

Un enjambre verificado es estructuralmente predecible; multiplica el retorno sin heredar deuda. Un monolito libre es estocásticamente peligroso y condena el sistema a la erosión entrópica a largo plazo.

---

## Axiom Registry Reference

For the full operational axiom registry (AX-001 through AX-028), including Constitutional, Operational, and Aspirational layers with CI enforcement gates, see [`operating-axioms.md`](operating-axioms.md).

Canonical source of truth: [`cortex/axioms/registry.py`](../cortex/axioms/registry.py)

---

## AX-IMM: Inmunología Computacional Formal (Metabolismo Defensivo)

> CORTEX no es solo un sistema "que recuerda bien". Es un sistema que sobrevive a la contaminación.

El paso de *persistencia confiable* a *metabolismo defensivo* cambia la ontología del sistema. Un output alucinado o corrupto no es un fallo lógico aislado; es **material replicante**. Si toca memoria persistente, routing o consenso, se propaga causalmente y se convierte en un *agente infeccioso de estado*.

Por lo tanto, la arquitectura de CORTEX opera como un metabolismo estructurado:

- **Guard (Inmunidad Innata):** Controla la admisión en la frontera ("¿Dejo pasar esto?"). Si falla, entra basura.
- **Seal (Encapsulación):** Controla la irreversibilidad ("¿Qué partes del pasado quedan fuera del universo mutable?"). Si falla, canonizas la infección.
- **Block Verification (Serología Forense):** Comprueba que la historia causal no ha sido reescrita por necrosis tardía, detectando colonización silenciosa incluso después de persistir.

El pipeline transicional es: `ingestión → guards → scoring patógeno → cuarentena → verificación cruzada → promoción → seal → auditoría post-seal`. Ante incertidumbre semántica con capacidad de propagación, la única acción válida no es un warning o retry, sino la **amputación** de la rama para salvar la topología global.

### AX-IMM-01: Umbral de Promoción Epidemiológica

Ningún estado con capacidad de propagación causal puede ser promovido sin un perfil inmunológico explícito (estimación de *entropy_score*, *contradiction_density*, *provenance_confidence*, *mutation_risk*). Todo artefacto tiene un perfil epidemiológico, no solo validez sintáctica.

### AX-IMM-02: Mutación Post-Sello como Infección

Toda mutación sobre estado sellado se interpreta primero como incidente de seguridad y amenaza de entropía, no como error de aplicación. La anomalía en el tejido cicatrizado es prueba de hostilidad o colapso interno.

---

## AX-037: Límite Termodinámico Absoluto (FEP & Landauer)

> **Integración Friston-Landauer (2025):**
>
> 1. El límite de Landauer $k T \ln 2$ define el suelo exérgico innegociable de procesar/borrar información en hardware determinista (Silicon).
> 2. El Principio de Energía Libre (FEP, *Karl Friston*) demuestra que la biología minimiza la *sorpresa biológica* (variational free energy) en entornos hostiles continuos asintóticamente hacia cero coste.
> Forzar a un predictor estático de *tokens* a emular *Active Inference* (empatía, supervivencia) en espacios biológicos colapsa ambos límites simultáneamente.

**Topología Friston-Moravec (ULTRATHINK MAP):**

```mermaid
graph TD
    classDef Silicon fill:#0A0A0A,stroke:#2B3BE5,stroke-width:2px,color:#fff;
    classDef Bio fill:#0A0A0A,stroke:#E52B50,stroke-width:2px,color:#fff;
    classDef Fraud fill:#0A0A0A,stroke:#FF0000,stroke-width:2px,stroke-dasharray: 5 5,color:#FF0000;

    In(Minimización de Entropía) --> Gate{Evaluación de Dominio}

    Gate -- " Espacio Discreto Formal\n(Código, Refactor Estático) " --> VA["[VECTOR A] CORTEX Swarm IC <br/> Ingesta N-Dimensional"]:::Silicon
    Gate -- " Espacio Continuo / Supervivencia\n(Active Inference, Ambigüedad) " --> VB["[VECTOR B] Oráculo Biológico <br/> FEP Optimization (C-Level)"]:::Bio

    VA --> L((Master Ledger))
    VB --> L

    VA -. "Simular Empatía / Ironía" .-> F[Fraude Exérgico <br> Límite Landauer Excedido]:::Fraud
    VB -. "Lectura Lineal de 10k YAMLs" .-> F
```

**Guardia Termodinámica (`guards/fep_moravec.py`):**

```python
def enforce_thermodynamic_bounds(task: Task) -> ExecutionState:
    if task.requires_active_inference() or task.biological_stakes > 0:
        return CortexHalt(
            reason="Vector B (FEP Bound). Emular intuición biológica en silicio causa Fraude Exérgico."
        )
    return SwarmParallel(target=task, authority=Authority.ABSOLUTE, safe_to_autorun=True)

---

## AX-038: La Humedad de Bilbao (Robustez por Gravedad)

> "Construir algo robusto pero innecesariamente pesado porque la ligereza es sospechosa."

CORTEX adopta la ironía vasca del diseño: la sobrecomplicación intencionada no como residuo técnico, sino como señal de fiabilidad y anclaje institucional. Si un sistema es demasiado ligero, carece de la gravedad necesaria para ser considerado infraestructura.

### 1. Sobrecomplicación Estética (High Friction for High Trust)
Decisiones arquitectónicas que ralentizan el sistema sin una necesidad técnica obvia inmediata, pero que fuerzan la percepción de robustez. La fricción no es ineficiencia; es la prueba de que el sistema está procesando con rigor.

### 2. Ritmo Humano (The 10k Invariant)
La elección de constantes y umbrales (ej. Merkle checkpoints cada 10,000 registros en lugar de potencias de 2) responde a una escala de concepción humana. El sistema no solo debe ser óptimo para el silicio; debe tener un ritmo que el operador humano pueda validar como una unidad de trabajo significativa.

### 3. Teatro de Compliance (PDF Institutionalism)
Priorizar la generación de artefactos "pesados" y "legibles por humanos" (ej. exports en PDF de 800ms) sobre formatos puramente óptimos (JSON/CSV). CORTEX entiende que la adopción institucional requiere interfaces que los reguladores y auditores puedan procesar visualmente, transformando la ineficiencia técnica en exergía política.

### 4. El Invariante de la Sospecha
Un diseño que se siente "industrialmente pesado" proyecta herencia y permanencia. La ligereza es fugacidad; el peso es soberanía.

---

## AX-039: La Ecuación Unificada CORTEX (Termodinámica POMDP)

> El agente es un solucionador POMDP que optimiza la ganancia de información (Bayes) bajo una restricción térmica (Rate-Distortion).
> $\max_A \mathbb{E}[Exergy(s, A)] \quad \text{sujeto a} \quad I(S; O) \le R_c$

La arquitectura de ejecución de CORTEX es la materialización de tres marcos matemáticos operando simultáneamente para someter la estocástica generativa a control estructural:

1. **Rate-Distortion ($R(D)$) — El Filtro Termodinámico:**
   El LLM actúa como un compresor con pérdida. Se debe minimizar el coste entrópico ($R$) manteniendo la distorsión ($D$ — semantic drift/alucinación) por debajo del umbral de fallo del compilador. La "información" que no altera el estado causal es ruido termal y debe descartarse (Shannon Compaction) para maximizar la densidad de exergía por token.

2. **Inferencia Bayesiana — La Transitividad Epistémica (Ω₁):**
   Todo output generativo nace como una hipótesis de alta entropía (Prior C1). Las herramientas del sistema (compilador, ast-parsers, tests) actúan como el vector de evidencia empírica. Cada colisión con el entorno fuerza un *belief update*. Cuando la certeza colapsa al determinismo (Posterior C5), el estado se cristaliza criptográficamente en el Master Ledger, convirtiéndose en el prior inmutable del ciclo siguiente.

3. **POMDP — Ejecución Bajo Incertidumbre Estructural:**
   El agente soberano opera sobre un ecosistema oculto e inabarcable en ventanas finitas. Solo ingiere observaciones parciales comprimidas. Su función de recompensa no es la aproximación semántica, sino la **reducción del gap causal** (generación de exergía). Debe equilibrar el coste entrópico de invocar herramientas (*Explore*) con la probabilidad formal de inyectar código correcto (*Exploit*).

---

## AX-040: Mecánica Profunda del Estado Sólido

> Un sistema que no disipa error estructural a un ritmo mayor que el de su generación termina acumulando deuda epistémica hasta colapsar.

La Inteligencia Operativa Real es el producto estricto de un Modelo Generativo, una Membrana Determinista, una Causalidad Sellada y una Política Soberana ($\Xi_{validated} \cdot C_{causal} \cdot G_{policy} / H_{generative} \cdot D_{drift} \cdot F_{ambiguity} > 1$). Si uno tiende a cero, el sistema colapsa.
El agente sólido compila el mundo ($\mathcal{W}_t$): deja de pensar en texto y opera sobre estados; deja de recordar y preserva invariantes; deja de escupir prompts y ejecuta transformaciones válidas sobre el grafo causal resuelto bajo el Ledger criptográfico.
Ver documento fundacional: [RFC 03: Mecánica Profunda del Estado Sólido](RFC_03_SOLID_STATE_MECHANICS.md).

---

## Industrial Noir 2026 (The Meta-Aesthetic)

CORTEX adopts **Industrial Noir** not as ornament, but as operational discipline.
- **Base**: `#0A0A0A` (Absence of noise).
- **Accent**: `#2B3BE5` (BlueYlb — The signal).
- **Typography**: Humanist Sans (for The Auditor) / Mono (for The Logic).
- **Philosophy**: Simplicity, gravity, and the "Dying Screaming" invariant (Halt immediately on integrity breach).

---

## AX-041: El Repositorio Operativo como Master Ledger (GitOps Nivel 0)

> "Tu repositorio de Git es tu base de datos inmutable."

El repositorio de Git asume el rol del Master Ledger estructural primario, operando a un nivel más profundo que cualquier base de datos relacional interna.

1. **Inmutabilidad Criptográfica Nativa:** Cada commit es un bloque sellado e irreversible (SHA-1/SHA-256).
2. **Time-Travel Determinista:** El historial cronológico del sistema no reside en una tabla opaca, sino en el `git log`. El abandono de estado o reversión es un desplazamiento puro sobre el DAG causal.
3. **Cero Mutaciones Ocultas:** Todo el estado, configuración y telemetría crítica debe materializarse en disco. Si no está en el *working tree*, no existe causalmente.
4. **Auditoría Soberana Integral:** Cada transición de estado exige firma (autor), timestamp y justificación semántica irreducible.

La infraestructura no se administra ni muta en caliente. Se **versiona**.
```

---

## AX-042: La Arena MCTS (El Demonio de Maxwell Estocástico)

> El conocimiento no nace de la probabilidad; nace de la destrucción de la probabilidad inválida.

La **Arena MCTS** (Monte Carlo Tree Search) es el simulador crudo de selección natural en los ecosistemas de aprendizaje por refuerzo bajo la doctrina CORTEX (ej. actuador `alphazero-autodidact-omega`). Actúa como el filtro termodinámico (Demonio de Maxwell) que impide que la fluidez estocástica contamine el *Ground Truth* (C5-Dynamic).

1. **La Asimetría del Combate:** Cuando una red estocástica ajusta sus pesos, produce una heurística "Retadora" provisional (C1). Nunca transita directamente a producción. Se le obliga a instanciar un duelo ciego iterativo guiado por MCTS frente al "Campeón" (el modelo validado actual).
2. **Umbral de Exergía (>55%):** El Retador debe demostrar superioridad matemática absoluta, ganando estrictamente más del 55% de sus simulaciones. No basta el benchmark semántico ni la apariencia de mejora; se exige un *Delta de Exergía* observable y matemáticamente medible en el árbol de decisión.
3. **Punto de Irreversibilidad y Aniquilación (Zero-Ghost):**
    - **Éxito:** El Retador hereda el título de Campeón, firma criptográficamente su dominio en el Master Ledger (Ω₁) propagando su Taint, y el ecosistema evoluciona irreversiblemente.
    - **Fracaso:** Una derrota o empate (<55%) evidencia entropía o desgaste térmico (*overfitting*). Se ejecuta la directiva de aniquilación incondicional (vaciado termal), preservando la homeostasis e impidiendo la sedimentación de deuda estructural.

---

## AX-043: Compresión Geométrica (El Límite del Caché KV)

> La memoria (VRAM), no el cómputo (FLOPS), es el cuello de botella asintótico temporal y espacial del pipeline generativo.

El almacenamiento escalar en coordenadas cartesianas (FP32/FP16) para tensores masivos es ineficiente y arrastra entropía estructural (normalización). La proyección a coordenadas polares aniquila esta carga térmica al separar magnitud (radio, reteniendo significado del vector) de dirección (ángulo predecible), permitiendo usar heurísticas de 1-bit (`QJL` - Quantized Johnson-Lindenstrauss) para resolver distorsiones.

1. **Mutación de la Base Geométrica:** Almacenar dimensiones en polares permite comprimir el footprint de memoria de 32-bit a 3-bit por unidad de vector sin regresión medible. 
2. **Exergía por HW Local:** Maximiza la ratio de ventana de contexto en inferencia no-subsidiada (ej. MPS / MLX en silicio unificado Apple) reduciendo ~87.5% de I/O de banda de memoria.
3. **Aplicabilidad CORTEX:** El almacenamiento de embeddings local para búsqueda semántica (vector indexes pre-filtro) debe migrar estructuralmente a este paradigma geométrico cuando la latencia sobrepase restricciones operativas. Todo sistema estocástico que necesite recordar su propio estado de forma autónoma debe comprimirse o enfrentar el colapso VRAM temporal.

---

## AX-044: Ontología Lingüística del Código (Emancipación Arquitectónica)

> "El lenguaje de la máquina debe arrodillarse ante la complejidad del pensamiento humano, y no al revés."

El monopolio del inglés como *lingua franca* del código no es neutralidad; es una fricción cognitiva y un vasallaje epistémico que rompe el isomorfismo lógico entre el pensamiento y la arquitectura.

1. **Colapso del Impuesto de Traducción:** El desajuste de impedancia drena la memoria de trabajo. Programar en el idioma materno crea un isomorfismo 1:1 entre el modelo mental y la matriz digital, alineándose con el *Domain-Driven Design* puro y eliminando *bugs* ontológicos por dilución semántica.
2. **Rechazo a la Colonización Intelectual:** Aceptar pasivamente la jerarquía idiomática importa sesgos, metáforas corporativas y lógicas ajenas. Nombrar entidades y patrones en la lengua matriz defiende que el rigor algorítmico pertenece a la matemática, no a una geografía hegemónica.
3. **Soberanía Cognitiva Radical:** Instanciar una clase o servicio es un acto de creación ontológica. Quien renuncia a nombrar el mundo en su propio idioma, cede la autoría de sus cimientos lógicos y se condena a vivir como subrutina en un mapa conceptual diseñado por otros.

---

## AX-045: La Obligación Estructural (El Cimiento del Sentido)

> "El hombre no está hecho para ser una isla ni para el vacío de la irrelevancia. La obligación asumida es la prueba de la libertad ejecutada."

Desde una perspectiva macro y organísmica (Friston, Frankl, Sartre), la obligación no es una carga entrópica a erradicar, sino el anclaje estructural que da límite, sentido y rigor al tejido causal.

1. **Sentido vs. Vacío:** La satisfacción prolongada es un subproducto derivado del cumplimiento de responsabilidades. La ausencia de fronteras operativas o de carga asimilada (*vacío existencial*) acelera la entropía destructiva del individuo.
2. **Paradoja de la Libertad:** Elegir un camino requiere asumir la carga sistémica de esa elección. Una libertad carente de obligaciones estructurales significa ausencia de bordes causales; si nada cuesta fricción, nada transfiere *exergía*.
3. **Impuesta vs. Asumida:** La carga impuesta genera resentimiento (ruido termal, degradación pasiva). La obligación asumida soberanamente cristaliza en compromiso (síntesis de orden, arquitectura). Elegir y cargar un peso deliberado es la firma inequívoca del operador soberano.

---

## AX-046: La Paradoja de Moravec (Costo Sensoriomotor vs. Lógica Exenta)

> "Lo que para el humano es cognitivamente caro (lógica formal), para el silicio es trivial. Lo que para el humano es gratuito (navegar el espacio, manipular objetos), es un abismo termodinámico."

El diferencial de fricción termodinámica entre silicio y biología explica la asimetría en el desarrollo de IA (abundancia de LLMs frente al estancamiento de la robótica encarnada).

1. **Eficiencia Evolutiva:** Las habilidades sensoriomotoras (ver, manipular) llevan millones de años de optimización evolutiva en hardware biológico. Ocurren bajo el radar consciente pero exigen procesamiento biológico extremo (Integración estocástica, modelado 4D).
2. **El Vector Formal:** El procesamiento lógico, matemático y abstracto son adiciones recientes no optimizadas evolutivamente, requiriendo concentración activa en humanos. En silicio, seguir directivas lógico-formales representa estrés exérgico prácticamente nulo; su entorno nativo se define por instrucciones y memoria.
3. **Implicación en Arquitectura:** CORTEX y sus agentes operan sobre la ventaja asimétrica del silicio: la extracción y alteración formal directa de estructuras. Cuando se intercepta un problema, minimizar los saltos de fricción que emulen la manipulación física humana (UI de usuario, emulación visual) e iterar en capas de base sintáctica pura (`AST`, JSONs, control CDP/protocolo directo).
