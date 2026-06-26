# MetaArbiter Specification

## 1. Definición Formal
El `MetaArbiter` es el mecanismo de consenso bizantino y selección topológica responsable de decidir la ramificación canónica cuando subagentes del Swarm producen estados concurrentes en conflicto.

## 2. Invariantes
- **Determinismo Arbitral**: Dadas dos o más ramificaciones con el mismo score matemático de confianza, el MetaArbiter debe usar una función de desempate determinista (ej. orden lexicográfico del hash del estado final) para asegurar que un replay seleccione siempre la misma rama.
- **Monopolio Causal**: Solo la rama elegida por el MetaArbiter es inyectada permanentemente a la línea principal del Ledger (`HEAD`).

## 3. Precondiciones
- Los nodos hoja de las ramas en conflicto deben haber superado las validaciones locales de Z3 SMT antes de llegar a la cola de arbitraje.

## 4. Complejidad
- **Temporal**: $O(K \times C)$ donde $K$ es el número de ramas en conflicto y $C$ es el coste de evaluar la heurística de confianza de cada rama.
- **Espacial**: $O(K)$.

## 5. Modos de Fallo
- **Empate Topológico (Deadlock)**: Fallo en la función determinista que bloquea el Swarm. Se soluciona forzando el desempate por *timestamp* criptográfico o hash.

## 6. Pruebas Asociadas
- Por implementar en la test suite de concurrencia.
