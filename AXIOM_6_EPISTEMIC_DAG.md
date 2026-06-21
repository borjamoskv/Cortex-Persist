# [C5-REAL] AXIOM 6: EPISTEMIC DAG ENFORCEMENT

> **"A Task without an Inference is arbitrary. An Inference without an Observation is hallucination."**

La ontología epistémica de CORTEX impone un Grafo Acíclico Dirigido (DAG) estricto para la cristalización de conocimiento y la mutación de estado.

## 1. Definición Formal de Nodos y Estados

### Observation (Evidencia Empírica)
Nodo raíz verificable derivado de evidencia física y determinista.
**Estados Epistémicos (Temporalidad):**
- `valid`: Empíricamente vigente.
- `stale`: Desfasado por la flecha del tiempo (ej. dependencia obsoleta), requiriendo validación, pero no intrínsecamente falso.
- `invalid`: Demostrado lógicamente o físicamente falso mediante un nuevo experimento.

### Inference (Derivación Causal)
Nodo derivado que conecta evidencia con acción o nueva lógica.

### Task (Mutación Físicamente Evaluable)
Nodo de acción y mutación de estado sobre el ecosistema.

## 2. Invariantes Matemáticas (Automaton Validator)

El **Epistemic Validator** evalúa el DAG exclusivamente bajo lógica proposicional de grafos, erradicando la evaluación semántica:

```text
∀ Inference I:
    ∃ Observation O:
        reachable(O, I)

∀ Task T:
    ∃ Inference I:
        reachable(I, T)

Graph(G) must be acyclic.
```

## 3. Topología de Precisión y Desgaste

El sistema de memoria no asume herencia implícita de certeza. Implementa métricas de degradación y distancia.

### Epistemic Depth (Deriva Estocástica)
Mide la distancia respecto a la evidencia física.
```text
depth(n) = 
    0                         if Observation
    1 + max(depth(parent))    otherwise
```
- **Intervención:** `depth > 5` → Requiere auditoría (Review). `depth > 10` → Ruptura estocástica (Requires Re-Observation).

### Epistemic Confidence (Fuerza Causativa)
Cada salto inferencial degrada la probabilidad de certeza, previniendo herencia estricta en sub-grafos especulativos.
`epistemic_confidence ∈ [0,1]` debe ser asignado y auditado por salto.

## 4. Apoptosis Celular y Propagación (Falsación Local)

Si el estado temporal o físico de una `Observation` fundacional (`O1`) muta a `stale` o `invalid`:

```text
status(closure(descendants(O1))) = status(O1)
```

Todos los nodos descendientes (tanto `Inference` como `Task`) en su sub-grafo se marcan mecánica y automáticamente. La propagación es local e incremental, eliminando la necesidad de reconstrucción total del modelo.
