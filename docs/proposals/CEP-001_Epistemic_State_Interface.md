<!-- [C5-REAL] Exergy-Maximized -->
# CEP-001: Arquitectura de Microkernel y Core Contracts

* **Id:** CEP-001
* **Título:** Arquitectura de Microkernel y Contratos del Núcleo
* **Estado:** Borrador (Draft)
* **Autor:** CORTEX Architecture Group
* **Fecha:** Junio 2026

## Principio Fundamental de Diseño
La arquitectura CORTEX se rige por el siguiente invariante: **Primero se definen los objetos; después se definen las transformaciones sobre esos objetos.** Las interfaces deben estabilizarse antes que los algoritmos que las implementan. El diseño actúa como un **microkernel con interfaces estables y servicios intercambiables**. El núcleo permanece pequeño, verificable y estable, mientras que las teorías de confianza, los motores de inferencia, los solvers o los renderizadores evolucionan de forma independiente respetando los contratos.

## 1. Core Object Model

Los `EpistemicObjects` son estructuras de datos puras, serializables e inmutables. Toda entidad que transite por el núcleo de CORTEX debe heredar de la interfaz abstracta `EpistemicObject` (ID único + Hash criptográfico de estructura).

```text
EpistemicObject
│
├── Assertion      (Declaración semántica pura sobre el dominio)
├── Evidence       (Artefacto observable que justifica una aserción)
├── Provenance     (Atribución, autoría, marcas temporales y origen)
├── Diagnostic     (Metadato sobre la salud, contradicciones o lagunas)
├── Constraint     (Invariante lógico o límite del sistema)
└── EpistemicState (Grafo de estado que consolida los objetos)
```

### El Contrato de `Assertion`
La `Assertion` es puramente semántica. **No debe contener ningún grado de confianza, probabilidad, score o peso.** La afirmación debe seguir siendo verdadera independientemente de las fuentes, pruebas, confianza, procedencia o teoría epistemológica actual. Toda la epistemología vive fuera de la afirmación:

* La `Assertion` es la proposición semántica.
* La `Evidence` justifica por qué creemos en la afirmación.
* El `EpistemicState` define el estado de esa creencia dentro del sistema.

Esquema conceptual:
```text
Assertion
  id
  subject
  predicate
  object
  context
  type
```

## 2. Core State Model

El `EpistemicState` es el objeto contenedor de la verdad parcial del sistema.

* **State Identity:** Identificador global único (UUIDv7 o URI determinista).
* **State Hash:** Hash criptográfico (SHA3-256) generado a partir del contenido de su grafo interno.
* **State DAG:** Las transiciones forman un Grafo Acíclico Dirigido (DAG) de estados históricos.
* **Transition Contracts:** Un `EpistemicState` es inmutable por diseño. Cualquier actualización genera un nuevo estado validado criptográficamente y anclado al anterior.

## 3. Execution Interfaces

Los componentes de ejecución están estrictamente separados de los objetos persistentes (`EpistemicObjects`). Esta separación garantiza que el límite entre datos (serializables) y ejecución no se difumine.

* **InferenceRule:** Reglas o lógicas puras. Una `InferenceRule` puede cambiar su implementación por completo sin alterar una sola `Assertion`.
* **InferenceEngine / Solver Interface:** Componentes ejecutables, como motores de inferencia o Proof Obligations, que procesan estados para generar nuevas aserciones o evidencias.
* **Trust Provider Interface:** Módulos que computan la confianza a partir de la evidencia, manteniéndola ortogonal a la aserción semántica.
* **Renderer Interface:** Componentes que abstraen la presentación del estado epistémico.

## 4. Kernel Contracts

El Kernel actúa como guardián de la integridad arquitectónica y orquesta las transiciones epistémicas.

* **Invariantes:** Los datos fluyen de forma apendicular. La mutación no destruye información pasada.
* **Panic Conditions:** El sistema abortará operaciones críticas (p. ej., mutaciones) si detecta:
  * Ausencia de un origen (`Provenance`) explícito.
  * Discrepancia entre el `root_hash` y los componentes estructurales del estado.
  * Modificación in situ de objetos ya integrados al grafo de estado histórico (violación del DAG).
* **Serialization & Compatibility:** Todos los objetos deben ser determinísticamente serializables y evolucionar mediante políticas de versionado que garanticen compatibilidad hacia atrás.
