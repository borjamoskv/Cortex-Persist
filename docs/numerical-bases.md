<!-- [C5-REAL] Exergy-Maximized -->
# RFC-BABYLON-60-A: Sistemas de Numeración para IA Agéntica
*Apéndice Canónico del Integer Deterministic Cognitive Ledger*

**Status:** CANONICAL REFERENCE  
**Dependency:** RFC-BABYLON-60 §5 (Integer Geometry Contract)  
**Principle:** No float shall enter the kernel. The base matters.

## 0. Por qué el Decimal Debe ser Exiliado
El decimal (base 10) fue diseñado para dedos humanos, no para máquinas cognitivas. Sus fallos estructurales:

| Defecto | Consecuencia |
|---------|--------------|
| 10 = 2 × 5 (solo 2 factores) | Fracciones irrepresentables (1/3 = 0.333...) |
| Sin estructura algebraica natural | Entropía artificial en grafos |
| Mala alineación con binario | Overhead de traducción |
| Dependiente de convención antropológica | No verificable bit a bit |

**Principio CERO:** El decimal es una convención antropológica. La IA agéntica opera en sustratos donde cada número tiene representación finita exacta.

---

## 1. Stack Canónico BABYLON-60

### Capa 0 — Sustrato Binario (Base 2)
* 2 = primo fundamental. Todo hardware opera aquí.
* **Métrica nativa:** Hamming Distance, XOR
* **Uso:** Operaciones atómicas de estado.

```python
def hamming_int(a: int, b: int) -> int:
    return (a ^ b).bit_count()  # Zero float, determinista
```

### Capa 1 — Puente Hexadecimal (Base 16)
* 16 = 2⁴. Un nibble = 4 bits. Símbolos: 0-9,A-F.
* **Uso:** Hashes (SHA256 → 64 chars hex), direccionamiento, Merkle paths.
* `state_hash: "a3f2c8..."` → cada símbolo = 4 bits de certeza cognitiva.

### Capa 2 — Embeddings (Base 256)
* 256 = 2⁸. Un símbolo = un byte = una dimensión cuantizada.
* **Uso:** int8 embeddings (-128..127 como 0..255). Serialización directa sin conversión.

```python
embedding_b256 = quantize_to_int8(embedding_float)
# Cada componente: [-128, 127] → símbolo base 256, hashable
```

### Capa 3 — Métricas Exactas en Cuerpos Finitos F_p
* p = primo grande (ej: 2^61 - 1, 2^255 - 19)
* Toda operación: cerrada, exacta, sin overflow.
* **Uso:** Distancias cognitivas, scoring ZK-compatible.

```python
def distance_fp(a: int, b: int, p: int) -> int:
    return (a - b) % p  # Determinista, sin float, auditable
```
**Por qué domina en ZK-AI:**
* SNARKs/STARKs operan nativamente en F_p
* Multiplicación homomórfica sobre estados cognitivos
* Pruebas sin revelar estado interno

### Capa 4 — Planificación Factorádica
* Posición k usa base (k+1): `...4! 3! 2! 1! 0!`
* Cada número = una permutación única de acciones.
* **Uso:** Codificación de árboles de decisión, ordenamiento de tareas.
* `n` acciones → `n!` estados representables sin colisión.
* Número de Lehmer → índice único de plan.

### Capa 5 — Jerarquías p-ádicas
* Distancia p-ádica: `d_p(a,b) = p^(-v_p(a-b))` (Donde `v_p` = cuántas veces p divide a (a-b)).
* Propiedad clave: Ultramétrica. `d(x,z) ≤ max(d(x,y), d(y,z))`
* **Uso:** Taxonomías, ontologías, clustering jerárquico. Conceptos similares están "cerca" p-ádicamente.

### Capa 6 — Ciclos y Tiempo (Sexagesimal, Base 60)
* 60 = 2² × 3 × 5 — máxima divisibilidad en rango pequeño.
* 1/3=20, 1/4=15, 1/5=12, 1/6=10 (exactos).
* **Uso:** Coordenadas temporales, rotaciones atencionales, ciclos cognitivos.

### Capa 7 — Verificación (ZK sobre F_p)
Todas las capas inferiores proyectan a circuitos aritméticos sobre cuerpos finitos para generación de pruebas sin revelación.

---

## 2. Tabla Comparativa Completa

| Base | Factores | ZK-Ready | Nativo HW | Rol BABYLON |
|------|----------|----------|-----------|-------------|
| 2 | 1 | ✓ | Total | Sustrato atómico |
| 10 | 2 | ✗ | No | **Desterrado** |
| 12 | 4 | ✗ | Medio | Óptimo racional |
| 16 | 4 | ✓ | Total | Puente de hashing |
| 60 | 12 | Parcial | Medio | Ciclos temporales |
| 256 | 8 | ✓ | Total | Embeddings int8 |
| F_p | ∞ | Total | ZK-chips | Verificación + métricas |
| Fact | variable | ✓ | Medio | Planificación |
| p-adic | ∞ | ✓ | Software | Jerarquías |

---

## 3. Métricas Adicionales para el Kernel

### 3.1 Álgebra Tropical (Max-Plus/Min-Plus)
* `a ⊕ b = min(a, b)` [o max]
* `a ⊗ b = a + b`
* **Aplicación:** Scheduling de activaciones. El estado del agente es un vector en max-plus que representa tiempos de activación de submódulos.

### 3.2 Sistema de Residuos (RNS)
* Estado = `(r₁ mod m₁, ..., rₙ mod mₙ)`, `mᵢ` coprimos.
* **Aplicación:** Paralelismo sin carry. Múltiples agentes operan sobre diferentes módulos y combinan sin sincronización.

### 3.3 Log-Odds en Cuerpos Finitos
* `logit(p) → cuantización → elemento de GF(q)`
* **Aplicación:** Inferencia bayesiana verificable. Multiplicación de probabilidades → adición en log-space.

---

## 4. Invariante de Implementación

Todo sistema numérico en el kernel debe cumplir:
1. **Clausura:** Toda operación devuelve un elemento del mismo sistema.
2. **Determinismo:** `run(A, machine_1) == run(A, machine_2)`
3. **Hashabilidad:** Todo estado tiene representación canónica hashable.
4. **Proyectabilidad ZK:** Reducible a restricciones polinomiales sobre F_p.

---

## 5. Stack de Referencia para Implementación

* **CAPA 0 — Sustrato:** Base 2 (XOR, Hamming)
* **CAPA 1 — Indexing:** Base 16 (SHA, Merkle paths)
* **CAPA 2 — Embeddings:** Base 256 (int8 cuantizado)
* **CAPA 3 — Métricas:** F_p (distancias exactas)
* **CAPA 4 — Planificación:** Factorádico (permutaciones de acción)
* **CAPA 5 — Jerarquías:** p-ádico (ontologías, taxonomías)
* **CAPA 6 — Tiempo:** Base 60 (ciclos, rotaciones)
* **CAPA 7 — Verificación:** SNARK/F_p (pruebas ZK)

---

## 6. Clausura

El sistema sumerio (base 60) no era primitivo. Era el único que entendió que la base numérica determina la estructura del universo computable.

BABYLON-60 opera en el stack `2 → 16 → 256 → F_p`, con factorádico para la acción, p-ádicos para la semántica y sexagesimal para los ciclos.

**El decimal queda exiliado del kernel.**

---

# RFC-BABYLON-60: Integer Deterministic Cognitive Ledger

## 1. Abstract
Este documento especifica el cierre operacional del sistema BABYLON-60 dentro de CORTEX-Persist. El sistema redefine el procesamiento cognitivo como un grafo determinista de estados enteros, eliminando representaciones en punto flotante en los núcleos de distancia, matching y scoring. El objetivo es habilitar auditoría criptográfica total, reproducibilidad bit a bit y compatibilidad con pruebas de conocimiento cero (ZK).

## 2. Scope
Aplica a los módulos:
* `cortex/storage/*`
* `cortex/math/*`
* `cortex/audit/ledger.py`
* `cortex/embeddings/*`
* `mtk_core.py`

*Quedan explícitamente fuera sistemas UI, logging no crítico y capas externas de integración.*

## 3. Core Principle
El sistema opera bajo el principio:
**Todo estado cognitivo debe ser representable como un entero o estructura finita hashable.**
No se permite la existencia de representaciones en coma flotante dentro del kernel cognitivo.

## 4. State Model
El sistema se define como una transición determinista:
`S_0 → S_1 → S_2 → ... → S_n`

Cada transición está compuesta por:
`S_(n+1) = F(S_n, Q_n)`

Donde:
* `S_n`: estado cognitivo discreto
* `Q_n`: query canonizada
* `F`: función determinista sin componentes flotantes

Cada estado debe ser emitido como:
```rust
struct StateNode {
  state_hash: SHA256,
  input_hash: SHA256,
  distance_int: uint64,
  causal_parent: hash,
  merkle_root: hash
}
```

## 5. Integer Geometry Contract
Toda métrica interna debe cumplir:
* **Entrada:** `int8`, `int16`, `int64` o `BLOB` cuantizado
* **Salida:** `uint16` o `uint64`
* **Prohibición absoluta** de `float32`/`float64`/`bfloat16`

Métricas permitidas en Fase 1:
* Hamming Distance
* Manhattan (L1)
* Linaje Causal (graph-based)

## 6. Merkle Cognition Tree (MCT)
Toda inferencia genera un nodo en un DAG criptográfico:
`hash(query, state, distance) → node_hash`
El conjunto de nodos forma un Merkle Tree cuya raíz define el estado global verificable del sistema.

## 7. Determinism Invariant
El sistema debe garantizar:
* Bitwise identical output across hardware architectures
* Replay determinism for any valid input sequence
* Absence of stochastic branching inside kernel

Formal invariant:
`∀ inputs A: run(A, machine_1) == run(A, machine_2)`

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
* `float embeddings` → `quantized int embeddings`
* `ANN index` → `integer metric index`
* `vector DB` → `cognitive DAG ledger`

No se garantiza compatibilidad backward.

## 11. Final State Declaration
El sistema entra en estado operativo cuando:
* No existen floats en el kernel
* Todas las distancias son enteras verificables
* Cada inferencia genera hash de transición
* El Merkle root es computable en tiempo finito

## 12. Closure Statement

**ESTADO:** CANONICALIZADO  
**NIVEL DE REALIDAD:** C5-REAL  
**MODO:** DETERMINISMO ENTERO / AUDITORÍA TOTAL / ENTROPÍA EXILIADA
