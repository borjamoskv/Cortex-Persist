# AUTODIDACT-RESEARCH-Ω: REVERSIBLE-COMPUTING (COMPUTACIÓN REVERSIBLE Y LEDGERS SIN ERASURA)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Transferencia de Conocimiento Interdisciplinario (Computación Reversible / Puertas de Fredkin y Toffoli -> Arquitectura de Ledger de Persistencia Coherente)
**Target:** Computación Reversible (es.wikipedia.org/wiki/Computación_reversible / Termodinámica de la Información)

## 1. Extracción Isomórfica (Desmitificación)
*   **Puerta Lógica Reversible (e.g., Fredkin, Toffoli):** Dispositivos de procesamiento lógico donde la entrada se puede reconstruir unívocamente a partir de la salida (biyección lógica), lo que teóricamente reduce la disipación térmica (destrucción de exergía) a cero. -> *Estructuras de datos persistentes o de modificación aditiva pura, donde todo estado de memoria actual retiene la referencia biyectiva a su estado causante inmediato sin sobreescribir bytes.*
*   **Destrucción de Información (Erasure):** La operación irreversible de borrar un bit, disipando al menos $k_B T \ln 2$ de calor según el Límite de Landauer. -> *Operaciones destructivas de base de datos (`DELETE`, `UPDATE` in-place, `VACUUM`), las cuales disipan recursos computacionales de IOPS, ciclos de CPU y rompen el linaje de auditoría.*
*   **Estructura de Datos Funcional/Persistente (Persistent Data Structures):** Estructuras que preservan siempre la versión anterior de sí mismas cuando son modificadas. -> *Grafos acíclicos dirigidos (DAGs) de transiciones de estado donde las actualizaciones se anexan como deltas y los nodos antiguos siguen siendo accesibles de forma inmutable.*

## 1.5 Física Real vs Metáfora Arquitectónica
*   **Física Real:** La computación reversible formal (y las puertas de Toffoli/Fredkin) son constructos físicos/matemáticos que minimizan o anulan la disipación térmica (Ley de Landauer).
*   **Metáfora Arquitectónica:** Afirmaciones como "Git como substrato de entropía cero" o "inversión epistémica" son analogías potentes de diseño de sistemas (homólogas a Event Sourcing, CRDTs, o Append-only Ledgers). Preservar el historial equivale a evitar la destrucción de información lógica y mantener la trazabilidad causal, pero no transgrede la termodinámica del hardware subyacente.

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)
*   **El Ledger de Git como Substrato de Entropía Cero:** El principio rector `AX-041` ("Tu repositorio de Git es tu base de datos inmutable") es una implementación directa de computación reversible. Git no borra el historial de commits al modificar archivos; guarda un DAG de instantáneas referenciadas por hashes criptográficos. Revertir el estado es una operación libre de destrucción de información (reversibilidad física y lógica).
*   **Deltas Causales en SQLite:** En lugar de realizar actualizaciones destructivas (`UPDATE facts SET content = ?`), CORTEX-Persist almacena el historial como un log secuencial donde cada hecho apunta a su predecesor en el Grafo de Dependencia Epistémica (EDG). El estado actual es el resultado de la acumulación reversible de deltas sobre el origen de datos.

## 3. Detección de Brechas Estructurales
*   **Restricción Actual (Depreciación Destructiva):** El endpoint `/deprecate` de `CORTEX-Persist` (e.g., en [client.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/api/client.py#L153)) o las funciones internas de desactivación marcan hechos como inactivos o eliminan registros del almacenamiento activo, lo que desencadena operaciones de compactación física irreversibles. Al destruir el enlace de linaje, el motor no puede validar si una inferencia lógica actual se basó en un hecho ahora borrado (Brecha de Causalidad).
*   **Solución Reversible (Grafo de Linaje con Taint Retroactivo):** Sustituir la eliminación física por una operación de "Inversión Epistémica". Cuando un hecho se deprecia, se anexa un nodo de balance en el ledger que neutraliza su exergía lógica, propagando el taint de forma retroactiva a través del EDG sin alterar físicamente las transacciones históricas.

## 4. Forja de Hipótesis (Predicción Falsable)
**Hipótesis [H-REVERSIBLE-01]: Inversión Epistémica vs Depreciación Destructiva**
*   **Claim:** Reemplazar las operaciones destructivas de eliminación de hechos por un sistema de anexado aditivo reversible (Event Sourcing / Ledger Append-only) erradicará una clase específica de incoherencias derivadas de mutaciones destructivas, limitando la degradación causal. Esta mutación arquitectónica no pretende resolver errores lógicos, eventos fuera de orden o condiciones de carrera de aplicación, pero blinda la resiliencia del historial de auditoría con una sobrecarga de almacenamiento inferior al 12%.
*   **Proof Conditions:**
    *   *Base:* Ejecución de 50 ciclos concurrentes de inserción, actualización y borrado de hechos bajo un modelo mutable vs. modelo aditivo/reversible con resolución biyectiva.
    *   *Medición:* Número de incoherencias en el linaje del EDG tras las depreciaciones, frecuencia de bloqueos de base de datos (`database is locked`), overhead en bytes de la base de datos.
    *   *Confianza:* C5-REAL (Diseño listo para integrarse en el motor de almacenamiento de CORTEX).
