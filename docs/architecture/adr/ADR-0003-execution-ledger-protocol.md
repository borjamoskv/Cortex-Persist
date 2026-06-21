# ADR-0003: C5 Execution Ledger Protocol

**Computational Jurisprudence & Semantic Replay**

## Status
**Accepted**

## Purpose
Establecer la transición definitiva desde un grafo de ejecución basado en estados hacia un modelo de **Jurisprudencia Computacional**. El grafo ya no es el control plane soberano; el grafo es una **proyección derivada (Projection Layer)** del **Event Log**.

## Core Axioms

### A1: Log is Reality
El sistema carece de un estado persistente autónomo. Solo existe la historia verificable. La realidad del sistema es el **ledger verificable**, no cualquier derivación puntual del runtime.

Fórmula canónica:
```text
State = Replay(Ledger, snapshot?)
```

### A2: Graph as Projection
La arquitectura de agentes no muta el estado final. Muta el Ledger mediante la agregación apendicular de eventos verificables. El Graph Engine solo materializa la vista de lectura temporal para evaluar la próxima acción.

### A3: Snapshot Accelerators
Para mitigar el **Ledger Bloat**, el sistema utiliza Snapshots de Aceleración.
El **Cold Ledger** es irreversible y NUNCA se elimina (preservando A1).
El **Semantic Snapshot** permite el arranque rápido (Runtime Bootstrap), derivando el estado sin reprocesar toda la historia, pero sin sustituir a la misma.

---

## Architectural Definitions

### 1. The Immutable Kernel

```python
class EventEnvelope:
    schema_version: int
    payload: bytes
    jurisdiction_signature: str

class Event:
    node_id: str
    input_state: dict
    output_diff: dict
    prev_hash: str
    hash: str  # Cryptographic Integrity

class Ledger:
    def append(self, event: Event) -> None: ...
    def verify_chain(self) -> bool: ...
    def replay(self, upto_hash: str) -> State: ...

class ProjectionEngine:
    def materialize_graph(self, ledger: Ledger) -> Graph:
        """Deriva el grafo como proyección del log"""
    
    def hash_projection(self, graph: Graph) -> str:
        """
        ProjectionHash = SHA256(GraphTopology + EdgeSet + NodeMetadata)
        Asegura que el mismo ledger siempre derive el mismo grafo.
        """

class SovereignKernel:
    def step(self):
        event = execute_node()
        self.ledger.append(event)
        self.state = self.ledger.replay(latest_hash)
```

### 2. Semantic Advisory (Semantic Witness)
El hashing de los eventos se complementa con Embeddings, pero la semántica es estrictamente consultiva, NUNCA autoritativa. La criptografía manda; la semántica solo alerta.

Para ser operable, el testigo semántico debe definir:
* **Embedding Model Versionado**: (ej. `text-embedding-3-small-v1`)
* **Canonical Serializer**: Algoritmo exacto para textificar el state diff antes de vectorizar.
* **Similarity Threshold**: Umbral de deriva (ej. `cosine_similarity < 0.85`).
* **Política de Rechazo**: Si cruza el umbral, el sistema alerta de `Semantic Drift` pero NO aborta el hash criptográfico primario.

```python
class SemanticWitness:
    embedding_model_hash: str
    vector_hash: str
    canonical_serializer_version: str
    similarity_threshold: float
```

### 3. Approximate vs. Deterministic Replay
Solo es determinista si se registra la totalidad del contexto entrópico. El motor de Replay registra explícitamente:

```python
class ModelFingerprint:
    provider: str
    model: str
    seed: int
    temperature: float
    tokenizer_hash: str
    weights_hash: str
    prompt_hash: str
    tool_outputs_hash: str
    api_timeouts_ms: int
```
Sin esto, el replay es una ilusión. Resultados de Replay: `REPRODUCIBLE` o `APPROXIMATE_REPLAY`.

---

## Acceptance Invariants

* **I1. Append-Only**: Ninguna mutación destructiva está autorizada físicamente.
* **I2. Hash-Chain Continuity**: Todo evento `n` debe incluir el hash exacto validado de `n-1`.
* **I3. Replayability**: `State_N` siempre debe ser reconstruible bit a bit desde la Génesis o un Snapshot criptográfico.
* **I4. Tool-Call Provenance**: Todo efecto colateral debe rastrearse a un output determinista registrado.
* **I5. Semantic Drift Detection**: Divergencias en el vector espacial se marcan permanentemente.
* **I6. Snapshot Integrity**: Todo Snapshot debe firmar criptográficamente el hash de estado del ledger en ese punto temporal.

---

## Event Execution Lifecycle

1. **Inception**: Observación ingresa al sistema.
2. **Graph Materialization**: `ProjectionEngine` proyecta el estado actual leyendo desde la génesis (o último Snapshot) hasta `HEAD`. Se valida el `ProjectionHash`.
3. **Cognition**: El nodo computa, inyectando outputs estáticos al `ModelFingerprint`.
4. **Crystallization**: Produce un `Event` en su correspondiente `EventEnvelope`.
5. **Chain Link**: El evento enlaza con el `prev_hash` y se añade al log.
6. **Re-Materialization**: El sistema colapsa y vuelve a reconstruirse para el siguiente step.
    
    ```text
    Event Log -> Reconstructs -> Graph -> Derives State
    Graph -> Emits Events -> Ledger
    State is never authoritative; it is a derived projection.
    ```

---

## Failure Modes & Expert Guardrails

### F1: Tool Nondeterminism
* **Amenaza**: Respuestas de red variables arruinan la reproducibilidad.
* **Mitigación**: `tool_outputs_hash` debe integrarse rígidamente en el bloque de replay.

### F2: Snapshot Poisoning
* **Amenaza**: Inyección de estado sintético malicioso en un macro-evento.
* **Mitigación**: El snapshot debe ser siempre reversible y cruzado con el hash-chain original en background.

### F3: Replay Divergence Across Model Versions
* **Amenaza**: `gpt-4-0613` reemplazado por OpenAI destruye el replay.
* **Mitigación**: Cambio de `REPRODUCIBLE` a `APPROXIMATE_REPLAY`. Alertar de bifurcación ontológica.

### F4: Audit Lag Under Load
* **Amenaza**: Validación del `ProjectionHash` retrasa asíncronamente el event loop en throughput masivo.
* **Mitigación**: Auditoría Shadow asíncrona; escrituras marcadas como optimistas hasta liquidación.

---

## Result
La arquitectura transita de agentes que mutan estado opaco a infraestructura de realidad computable. Toda decisión de CORTEX queda registrada como evento, precedente y evidencia verificable. El sistema no preserva "estado" como fuente de verdad; preserva historia causal reproducible.
