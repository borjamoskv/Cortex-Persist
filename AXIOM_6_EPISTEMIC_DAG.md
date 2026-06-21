# [C5-REAL] AXIOM 6: EPISTEMIC DAG ENFORCEMENT

> **"A Task without an Inference is arbitrary. An Inference without an Observation is hallucination."**

La ontología epistémica de CORTEX impone un Grafo Acíclico Dirigido (DAG) estricto para la cristalización de conocimiento y la mutación de estado.

## Estructura Causal Formal

- **`Observation`**: Nodo raíz verificable derivado de evidencia física, determinista y reproducible (ej. un estado del AST, un código de error de SQLite, un hash criptográfico).
- **`Inference`**: Nodo derivado que debe poseer al menos un ancestro `Observation` alcanzable en el DAG.
- **`Task`**: Nodo de acción que debe poseer al menos un ancestro `Inference` alcanzable en el DAG.

## Transiciones de Estado y Prohibiciones (Forbidden)

El **Epistemic Validator** bloqueará topologías que no cumplan los siguientes invariantes:

1. `Task` sin ancestro `Inference` en el grafo causal.
2. `Inference` sin ancestro `Observation` en el grafo causal.
3. Ciclos epistemológicos.
4. Autojustificación recursiva (`Inference -> Inference -> Inference` ad infinitum sin anclaje en la realidad física).

## Corolario (Falsación Local y Propagación)

Si una `Observation` fundacional (ej. `O1`) es invalidada o muta su estado, todos los nodos descendientes (tanto `Inference` como `Task`) en su sub-grafo se marcan automáticamente como estructuralmente sospechosos o inválidos. Este mecanismo de invalidación local previene la corrupción silente del conocimiento de dominio.
