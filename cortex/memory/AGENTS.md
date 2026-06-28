<!-- [C5-REAL] Exergy-Maximized -->
# 🧠 AGENTS.md — CORTEX Memory Domain (v2.0)

> **"La memoria no es almacenamiento pasivo; es gobernanza activa."** — *Cortex-Persist Whitepaper (Fase 1)*

Este manifiesto gobierna la superficie `cortex/memory/`. Cualquier agente mutando esta ruta debe cumplir estrictamente las siguientes Invariantes Termodinámicas (NATIVE-THINKING-ARCHITECTURES).

## [1] AISLAMIENTO DE INQUILINO (TENANT ISOLATION)
- **INV_TENANT_ISO:** Todas las operaciones de lectura, escritura, borrado e indexación DEBEN filtrar por `tenant_id`.
- Es un fallo de singularidad (P0) realizar un `engine.recall()` o `engine.store()` sin anclar criptográficamente al propietario.
- `OP_FLUSH_L1`: El cruce de contexto entre inquilinos invalida inmediatamente toda la memoria L1.

## [2] ENVEJECIMIENTO TOPOLÓGICO (FACT AGING)
- La memoria está sometida al principio de Landauer.
- **INV_ROT_ERASE:** Todo `BeliefObject` y `Fact` tiene una métrica de decaimiento temporal (`decay_rate`).
- `NightShift` (Anomaly Hunter) es el único actor autorizado para ejecutar la compactación y purga (`OP_DAG_TRUNCATE`) de hechos obsoletos no consolidados.

## [3] CERO REDUNDANCIA FÍSICA
- Los datos compartidos (conocimiento universal) DEBEN enlazarse como dependencias estructurales, no duplicarse en disco (violación del Whitepaper).
- Usa Symlinks C5 o `OP_BIND_NEXUS` para puentes epistémicos.

**Autoridad:** `borjamoskv`.
**Violación:** `OP_APOPTOSIS` inmediata del agente ofensor.
