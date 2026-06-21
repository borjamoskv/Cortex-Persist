# C5 Execution Ledger Protocol v0.2

## 1. Core Axiom & Canonical Architecture

```text
Event Log -> Reconstructs -> Graph -> Derives State
Graph -> Emits Events -> Ledger
```

**State is never authoritative; it is a derived projection.**

---

## 2. Event Envelope Specification

Todo evento debe encapsularse estructuralmente antes de su cristalización en el Ledger:

```json
{
  "event_id": "uuid",
  "prev_hash": "sha256",
  "jurisdiction": "str",
  "schema_version": "v1",
  "payload": {
    "node_id": "str",
    "inputs": {},
    "diff": {}
  },
  "fingerprint": {
    "provider": "str",
    "model": "str",
    "seed": "int",
    "temperature": "float",
    "prompt_hash": "sha256",
    "tool_outputs_hash": "sha256"
  },
  "semantic_witness": {
    "embedding_version": "str",
    "vector_hash": "sha256"
  },
  "signature": "crypto_signature",
  "hash": "sha256"
}
```

---

## 3. Strict Invariants

| ID | Name | Constraint |
|---|---|---|
| **I1** | Append-Only | Ninguna mutación física destructiva (DELETE/UPDATE) es ejecutable. |
| **I2** | Hash-Chain Continuity | Todo evento `N` incluye validación estricta del hash `N-1`. |
| **I3** | Absolute Replayability | `State_N` es 100% derivable bit-a-bit desde `Génesis` o el último Snapshot criptográfico. |
| **I4** | Nondeterministic Containment | Efectos de red y APIs están contenidos vía `tool_outputs_hash`. |
| **I5** | Subpoena Jurisdiction | Modificaciones cruzadas entre dominios operan como solicitudes (`BRIDGE`), nunca como escrituras directas. |
| **I6** | Snapshot Integrity | Todo Snapshot ancla criptográficamente la historia precedente; su borrado no destruye la causalidad, solo degrada el rendimiento. |

---

## 4. Formalized Failure States

| ID | Threat | Mechanism | Severity |
|---|---|---|---|
| **F1** | Replay Divergence | Actualización silente de modelo anula el hash del estado derivado (`APPROXIMATE_REPLAY`). | EXISTENTIAL |
| **F2** | Semantic Drift | El vector de similitud espacial colapsa (`cosine < 0.85`), revelando alucinación ontológica. | HIGH |
| **F3** | Jurisdiction Override | Nodo intenta cristalizar evento con firma no autorizada para el namespace objetivo. | CRITICAL |
| **F4** | Snapshot Poisoning | Falsificación de estado en un Snapshot acelerador asíncrono. | CRITICAL |
| **F5** | Network Nondeterminism | Herramientas devuelven resultados variables sin estar hasheadas en el `ModelFingerprint`. | HIGH |

---

## 5. Protocol Test Matrix

* **T1. Genesis Replay Test**
  * *Acción*: Purgar Snapshots. Re-ejecutar Event Log desde índice 0.
  * *Assert*: `hash(State_New) == hash(State_Old)`.
* **T2. Nondeterministic Divergence Test**
  * *Acción*: Modificar `temperature` en `ModelFingerprint` durante Replay simulado.
  * *Assert*: Sistema marca el pipeline como `APPROXIMATE_REPLAY` y bloquea cristalización de nuevos events.
* **T3. Jurisdiction Breach Test**
  * *Acción*: Emitir evento `Finance` firmado por el dominio `Research`.
  * *Assert*: `ExecutionKernel` aborta en el `JurisdictionValidator` (Write Rejected).
* **T4. Semantic Poisoning Test**
  * *Acción*: Mutar sutilmente un payload preservando la sintaxis pero invirtiendo el sentido (ej. "Autorizar" -> "Denegar").
  * *Assert*: `SemanticWitness` detecta la caída por debajo del `similarity_threshold` (Semantic Drift Alert).
* **T5. Snapshot Irreversibility Test**
  * *Acción*: Destruir el último Semantic Snapshot.
  * *Assert*: El sistema arranca degradado en latencia (reprocesando desde Génesis o Snapshot previo) pero `State` converge idéntico.
* **T6. Broken Chain Link Test**
  * *Acción*: Inyectar un evento sintético con `prev_hash` inválido.
  * *Assert*: Ledger rechaza el evento instantáneamente (`Hash-Chain Continuity Violation`).
