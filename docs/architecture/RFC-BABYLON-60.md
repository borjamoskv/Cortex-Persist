# RFC-BABYLON-60: Integer Deterministic Cognitive Ledger

**ID:** RFC-BABYLON-60  
**Status:** CANONICAL / FINAL  
**Layer:** Core / Storage / Logic  
**Dependencies:** `cortex-persist-v2.0`  
**Invariants:** Zero-Float, Bit-Identity, ZK-Proof Ready  

## 1. Abstract
Este documento especifica el cierre operacional del sistema **BABYLON-60** dentro de `cortex-persist`. El sistema redefine el procesamiento cognitivo como un grafo determinista de estados enteros, eliminando representaciones en punto flotante en los núcleos de distancia, matching y scoring. El objetivo es habilitar auditoría criptográfica total, reproducibilidad bit a bit y compatibilidad nativa con pruebas de conocimiento cero (ZK).

## 2. Scope
Aplica estrictamente a los siguientes módulos del núcleo:
* `cortex/storage/*`: Motores de persistencia y serialización.
* `cortex/math/*`: Funciones de cálculo de distancia y métricas.
* `legacy_research/audit/ledger.py`: Registro de transiciones de estado.
* `cortex/embeddings/*`: Capas de cuantización y proyección entera.
* `mtk_core.py`: Núcleo de transformación de estados.

*Exclusiones:* Sistemas de UI, telemetría no crítica y adaptadores de integración externos que no afecten el kernel cognitivo.

## 3. Core Principle
El sistema opera bajo el axioma fundamental de **Integridad Discreta**:
> "Todo estado cognitivo debe ser representable como un entero o una estructura finita hashable. No se permite la existencia de representaciones en coma flotante (IEEE 754) dentro del kernel cognitivo."

## 4. State Model
El sistema se define como una transición determinista de estados finitos:
`S_0 → S_1 → S_2 → ... → S_n`

Donde cada transición se rige por:
`S(n+1) = F(S_n, Q_n)`

**Parámetros:**
* **S_n:** Estado cognitivo discreto (vector de enteros cuantizados).
* **Q_n:** Query canonizada (normalizada a nivel de bits).
* **F:** Función determinista pura sin componentes estocásticos o flotantes.

**Estructura del Nodo de Estado (StateNode):**
```rust
struct StateNode {
    state_hash:   SHA256,    // Hash del estado actual
    input_hash:   SHA256,    // Hash del input/query que disparó el cambio
    distance_int: uint64,    // Métrica de distancia en dominio entero
    causal_parent: Hash,      // Puntero al estado anterior (S_n-1)
    merkle_root:  Hash       // Raíz del Merkle Cognition Tree
}
```

## 5. Integer Geometry Contract
Toda métrica interna de similitud o relevancia debe cumplir con el contrato de geometría entera:

* **Entradas:** Vectores de `int8`, `int16`, `int64` o BLOBs cuantizados.
* **Salidas:** `uint16` o `uint64`.
* **Prohibición:** Bloqueo total de `float32`, `float64`, `bfloat16` en el path de ejecución crítica.

**Métricas autorizadas en Fase 1:**
1. **Hamming Distance:** Para búsquedas binarias rápidas.
2. **Manhattan Distance (L1):** Para proyecciones lineales.
3. **Linaje Causal:** Basado en la profundidad del grafo de hashes.

## 6. Merkle Cognition Tree (MCT)
Toda inferencia o movimiento dentro del espacio latente genera un nodo en un Grafo Acíclico Dirigido (DAG) criptográfico:

`hash(query_id, previous_state_hash, distance_result) → node_hash`

El conjunto de nodos forma un **Merkle Tree**. La raíz de este árbol (`Merkle Root`) define el estado global verificable del sistema en cualquier punto del tiempo, permitiendo la verificación de "Prueba de Cognición".

## 7. Determinism Invariant
El sistema garantiza las siguientes invariantes:
1. **Hardware Independence:** El output es idéntico bit a bit en arquitecturas ARM64, x86_64 o RISC-V.
2. **Replay Determinism:** Dada una secuencia idéntica de inputs, el estado final del ledger es idéntico.
3. **Entropy Exile:** Se prohíben semillas aleatorias (seeds) no versionadas o fuentes de entropía no controladas dentro del kernel.

**Formal Invariant:**
`∀ inputs A: run(A, machine_1) == run(A, machine_2)`

## 8. ZK Compatibility Layer
Todas las operaciones están diseñadas para ser proyectables a circuitos aritméticos:
* Uso de elementos de **Cuerpo Finito (Finite Fields)**.
* Compatibilidad con restricciones de circuitos **SNARK/STARK**.
* Reducción de transiciones a restricciones polinomiales hashables.

## 9. Failure Modes (Critical)
Se consideran violaciones críticas que invalidan el ledger:
* Inyección accidental de un valor `float` en el path del kernel.
* Uso de semillas de hashing no deterministas (ej. `hash(id(obj))`).
* Mutación de esquemas sin incremento de versión en el ledger.
* Funciones de distancia que no devuelvan el mismo entero ante el mismo input.

## 10. Versioning & Migration
BABYLON-60 representa una ruptura estructural.

**Protocolo de Migración:**
* **Embeddings:** Transformación obligatoria de `float32` a `int8/int16` mediante cuantización por proyección.
* **Indexing:** Sustitución de índices ANN probabilísticos por índices métricos enteros deterministas.
* **Storage:** Transición de bases de datos vectoriales tradicionales a un **Cognitive DAG Ledger**.

## 11. Final State Declaration
El sistema se considera operativo (`LIT`) cuando:
1. El analizador estático confirma **zero-float** en `cortex/math/`.
2. Las pruebas de cross-platform devuelven **hashes de estado idénticos**.
3. El Merkle Root es computable y verificable en menos de 10ms por transición.

## 12. Closure Statement
```text
ESTADO: CANONICALIZADO
NIVEL DE REALIDAD: C5-REAL
MODO: DETERMINISMO ENTERO / AUDITORÍA TOTAL / ENTROPÍA EXILIADA
```

---
*Firmado para el commit final de cortex-persist.*
