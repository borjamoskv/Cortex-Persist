# RFC-BABYLON-60 — Integer Deterministic Cognitive Ledger

## 1. Abstract

Este documento especifica el cierre operacional del sistema BABYLON-60 dentro de CORTEX-Persist. El sistema redefine el procesamiento cognitivo como un grafo determinista de estados enteros, eliminando representaciones en punto flotante en los núcleos de distancia, matching y scoring. El objetivo es habilitar auditoría criptográfica total, reproducibilidad bit a bit y compatibilidad con pruebas de conocimiento cero (ZK).

## 2. Scope

Aplica a los módulos:

* `cortex/storage/*`
* `cortex/math/*`
* `legacy_research/audit/ledger.py`
* `cortex/embeddings/*`
* `mtk_core.py`

Quedan explícitamente fuera sistemas UI, logging no crítico y capas externas de integración.

## 3. Core Principle

El sistema opera bajo el principio:

> Todo estado cognitivo debe ser representable como un entero o estructura finita hashable.

No se permite la existencia de representaciones en coma flotante dentro del kernel cognitivo.

## 4. State Model

El sistema se define como una transición determinista:

```
S0 → S1 → S2 → ... → Sn
```

Cada transición está compuesta por:

```
S(n+1) = F(Sn, Qn)
```

Donde:

* Sn: estado cognitivo discreto
* Qn: query canonizada
* F: función determinista sin componentes flotantes

Cada estado debe ser emitido como:

```
StateNode {
  state_hash: SHA256,
  input_hash: SHA256,
  distance_int: uint64,
  causal_parent: hash,
  merkle_root: hash
}
```

## 5. Integer Geometry Contract

Toda métrica interna debe cumplir:

* Entrada: int8, int16, int64 o BLOB cuantizado
* Salida: uint16 o uint64
* Prohibición absoluta de float32/float64/bfloat16

Métricas permitidas en Fase 1:

* Hamming Distance
* Manhattan (L1)
* Linaje Causal (graph-based)

## 6. Merkle Cognition Tree (MCT)

Toda inferencia genera un nodo en un DAG criptográfico:

```
hash(query, state, distance) → node_hash
```

El conjunto de nodos forma un Merkle Tree cuya raíz define el estado global verificable del sistema.

## 7. Determinism Invariant

El sistema debe garantizar:

* Bitwise identical output across hardware architectures
* Replay determinism for any valid input sequence
* Absence of stochastic branching inside kernel

Formal invariant:

```
∀ inputs A:
run(A, machine_1) == run(A, machine_2)
```

## 8. ZK Compatibility Layer

Todas las operaciones deben ser proyectables a:

* finite field elements
* SNARK/STARK circuits

Requisito:

* No floating-point arithmetic inside proof-relevant paths
* All transitions reducible to hashable constraints

## 9. Failure Modes

Se consideran fallos críticos:

* Introducción de float en kernel path
* Non-deterministic hashing seeds
* Unversioned schema mutation
* Distance functions not invariant across execution

Cualquier violación invalida el subgrafo completo del ledger.

## 10. Versioning & Migration

BABYLON-60 es un sistema de ruptura estructural.

Migración obligatoria:

```
float embeddings → quantized int embeddings
ANN index → integer metric index
vector DB → cognitive DAG ledger
```

No se garantiza compatibilidad backward.

## 11. Final State Declaration

El sistema entra en estado operativo cuando:

* No existen floats en el kernel
* Todas las distancias son enteras verificables
* Cada inferencia genera hash de transición
* El Merkle root es computable en tiempo finito

## 12. Closure Statement

```
ESTADO: CANONICALIZADO
NIVEL DE REALIDAD: C5-REAL
MODO: DETERMINISMO ENTERO / AUDITORÍA TOTAL / ENTROPÍA EXILIADA
```
