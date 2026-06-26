# DivergenceMap Specification

## 1. Definición Formal
El `DivergenceMap` mide la distancia topológica $D(T_a, T_b)$ entre una ejecución canónica $T_a$ y una ejecución divergente o estocástica $T_b$. Es el motor de control estructural para swarms.

## 2. Invariantes
- **Cero Deriva Canónica**: La distancia de una traza consigo misma debe ser cero ($D(T_a, T_a) = 0$).
- **Monotonía de la Divergencia**: La divergencia sólo puede crecer o mantenerse estable conforme se agregan eventos estocásticos; nunca disminuir (salvo rollback explícito).

## 3. Precondiciones de Cálculo
- Ambas trazas $T_a$ y $T_b$ deben originarse de una raíz de estado (Merkle Root) en común.

## 4. Postcondiciones
- Si $D > Threshold$, se emite una señal de control `RE_ROUTE` o `STABILIZE` al MetaArbiter.

## 5. Complejidad
- **Temporal**: Depende del algoritmo de similitud (ej. Longest Common Subsequence). Clásicamente $O(A \times B)$ donde $A, B$ son la cantidad de eventos divergentes desde el ancestro común.
- **Espacial**: $O(A + B)$.

## 6. Modos de Fallo
- **Divergencia Absoluta**: Si las trazas no comparten un ancestro común verificable en el Ledger, la distancia es infinita (Indeterminable).

## 7. Pruebas Asociadas
- `tests/replay/test_replay_equivalence.rs`
