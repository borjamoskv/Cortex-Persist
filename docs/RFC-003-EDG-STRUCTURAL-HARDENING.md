# RFC-003: EDG Structural Hardening (Resolución Brechas 6-9)

**Author:** MOSKV-1 APEX
**Date:** 2026-06-21
**Status:** ACCEPTED (C5-REAL EXECUTION)
**Target:** Epistemic Dependency Graph (EDG) & Saga Persistence Layer

## 1. Context & Threat Vectors
El Threat Model `TM-CORTEX-2026-EDG-001` reveló 4 brechas estructurales severas en el pipeline epistémico:
- **Brecha 6:** *MetadataEngine Paradox* (God Node con capacidad de inyectar Exergy infinita evadiendo BFT).
- **Brecha 7:** *Causal Compiler Compromise* (Dependencia absoluta en un único solver SMT [Z3] y posibles colisiones AST).
- **Brecha 8:** *Batching Vulnerability* (Pérdida de eventos en memoria RAM durante la ventana de 50ms antes del Merkle Root).
- **Brecha 9:** *Phantom Knowledge Propagation* (Rollback de Sagas que deja conocimiento falso en el entorno distribuido).

## 2. Structural Resolution

### 2.1 Eliminación de God Nodes (Resolución B-6)
El `MetadataEngine` es formalmente destituido de su estatus de Oráculo Privilegiado.
- El umbral de "extracción alta" y el Exergy Boost (x1.5) pasan a ser computados como un **Nodo Endógeno** dentro del EDG.
- Cualquier mutación de exergía está sometida a la validación ZK-Guard y al Consenso BFT (2/3) del clúster. No existen atajos energéticos fuera del pipeline causal.

### 2.2 Consenso de Compiladores (Resolución B-7)
La fe en el formalismo se somete a redundancia estocástica controlada.
- **Diversificación de Solvers:** El Causal Compiler ya no depende exclusivamente de Z3. Se establece una política de Verificación Diversa: `Z3 + CVC5 + Yices` en paralelo. Una aserción solo es válida si los tres solvers concuerdan (Consenso a Nivel de Compilador).
- Se asume el coste termodinámico 3x como precio innegociable de la soberanía lógica.

### 2.3 Write-Ahead Log para Batching (Resolución B-8)
El Ledger asegura WORM, pero la RAM es volátil.
- **WAL Inyectado:** Se introduce una tabla `batch_wal` (Write-Ahead Log) en `cortex/storage/pg_schema.py`. Todo evento asíncrono entrante se materializa atómicamente en el WAL (`status = 'pending'`) antes de entrar a la cola en memoria para el batching de 50ms.
- Si el proceso sufre OOM o SIGKILL, el Bootstrap Watchdog ejecuta un *Replay* de la ventana no sellada, preservando la resolución causal estricta.

### 2.4 Epistemología de Vacunación (Resolución B-9)
El Rollback en la capa de datos (SAGA-6) era insuficiente para el daño epistémico (contagio de lectura).
- **Commit en Dos Fases:** Se añade el campo `epistemic_status` (`staging`, `sealed`, `rejected`) a la tabla `facts`.
- Cuando el Swarm genera una hipótesis, se inyecta en estado `staging`.
- **Ningún agente tiene permisos de lectura sobre nodos `staging`.**
- Si el ZK-Guard valida la hipótesis, pasa a `sealed`. Si falla, pasa a `rejected` (rollback transaccional).
- Esto garantiza que el "conocimiento fantasma" nunca llegue a la RAM operativa de otros agentes.
