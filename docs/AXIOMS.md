# Axioms — CORTEX Persist

Package: cortex-persist v0.3.0b1 · Engine: v8
License: Apache-2.0 · Python: >=3.10

> Epistemic and design doctrine.
>
> Related: [`AGENTS.md`](../AGENTS.md) · [`operating-axioms.md`](operating-axioms.md) (AX-001–AX-028)

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

Full treatment: [`cortex/axioms/registry.py`](../cortex/axioms/registry.py)

---

## AX-035: Ontología de la Capacidad (Ingeniería de Interfaz vs. Prompting)

> Una capacidad nueva no es una respuesta mejor. Es una nueva forma estable de transformar estado.

Las capacidades de un sistema soberano no nacen de inyectar más *tokens* o diseñar *prompts* más largos ("maquillaje con esteroides"). Se materializan cuando una fricción recurrente se formaliza en un protocolo compuesto, verificable y transferible.

Una verdadera **Capacidad (Skill/Agent)** surge de acoplar invariablemente cinco capas:

1. **Modelo**: Razonamiento, contexto, *tool-use*.
2. **Memoria/Estado**: Acumulación de contexto útil frente a "respuesta suelta".
3. **Herramientas**: Mutación de estado real (APIs, filesystem, web).
4. **Contratos/Evaluación**: Schemas, validadores, *guardrails*, criterios de éxito.
5. **Orquestación**: Control de flujo (observar, decidir, abortar).

**El Criterio de Falsabilidad de una Capacidad:**
Si un comportamiento no define qué entrada recibe, qué salida válida produce, qué herramientas orquesta y bajo qué condiciones exactas debe **abortar**, no es una capacidad: es un **ritual narrativo**. La novedad no reside en hacer más cosas; reside en aislar una transformación de estado y volverla estable, invocable y verificable (Nivel 1+).

---

## Axiom Registry Reference

For the full operational axiom registry (AX-001 through AX-028), including Constitutional, Operational, and Aspirational layers with CI enforcement gates, see [`operating-axioms.md`](operating-axioms.md).

Canonical source of truth: [`cortex/axioms/registry.py`](../cortex/axioms/registry.py)

---
