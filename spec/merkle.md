# Merkle Provenance Specification

## 1. Definición Formal
El `Merkle Provenance` es la estructura arbórea utilizada para verificar la integridad topológica del Ledger en CORTEX-PERSIST. Convierte el historial lineal de eventos en un árbol binario de hashes de acceso optimizado.

## 2. Invariantes
- **Determinismo Hash**: El hash de un nodo interno $H(padre)$ debe ser estrictamente $SHA256(H(hijo\_izquierdo) || H(hijo\_derecho))$.
- **Estabilidad de la Raíz**: Para un conjunto idéntico de eventos $E_{0..N}$, el `stored_root` $R$ debe ser matemáticamente idéntico independientemente de las condiciones de ejecución.

## 3. Precondiciones para Inclusión
- El evento hoja debe ser insertado en el Ledger antes o atómicamente con la actualización del árbol.
- El índice de la hoja debe coincidir con su posición topológica en la secuencia de ejecución.

## 4. Complejidad
- **Espacial**: $O(N)$ para almacenar el árbol completo en memoria/disco, siendo $N$ el número de eventos.
- **Temporal (Cálculo de Raíz)**: $O(\log N)$ para actualizar la raíz tras un append.
- **Temporal (Prueba de Inclusión)**: $O(\log N)$. Verificar cualquier observación es una operación logarítmica respecto al tamaño del historial.

## 5. Modos de Fallo
- **Asimetría de Raíz**: Tras un replay determinista, si $R_{replay} \neq R_{stored}$, la ejecución se considera divergente y se descarta el árbol corrupto.

## 6. Pruebas Asociadas
- `tests/replay/test_merkle_root.rs`
- `tests/replay/test_hash_chain.rs`
