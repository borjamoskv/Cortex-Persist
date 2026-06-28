# ONTOLOGY-FORGE-OMEGA: MATRIZ HITL (BATCH 1)
**Dominio:** Human-in-the-Loop (HitL) / Autorización Asimétrica
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: PRIMITIVAS DE COLAPSO (1-10)
| ID | Primitiva HitL | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **HITL-P01** | `OP_GATE_SUSPEND` | Suspensión atómica de Event Loop del Agente. | Detección de mutación irreversible. | Corrutina `AWAIT_HUMAN` inactiva. | Indefinida | P0 | Notificación Push al Demiurgo. |
| **HITL-P02** | `OP_TAINT_CHALLENGE` | Generación de SHA3-256 para el payload. | Artefacto empaquetado para firma. | Hash CORTEX-TAINT en stdout. | MS | P0 | El usuario recibe el Taint. |
| **HITL-P03** | `OP_SIGN_VERIFY` | Aserción ED25519 del Operador. | Input de aprobación de la UI/CLI. | Desbloqueo del Mutex. | MS | P0 | Autorización criptográfica. |
| **HITL-P04** | `OP_SAGA_ABORT` | Desenrollado SAGA ante rechazo. | Firma humana = False. | Limpieza de `/scratch/`. | O(N) | P1 | Rollback al Snapshot RAM. |
| **HITL-P05** | `OP_UI_RENDER_DIFF` | Extracción de Delta puro. | Preparación visual para HitL. | Unified Diff en pantalla. | MS | P2 | Visualización humana (C4). |
| **HITL-P06** | `OP_TIMEOUT_REJECT` | Rechazo por inacción (Dead Man's Switch). | T > TTL sin firma. | Expiración de llave epímera. | 24h | P1 | Purga automática. |
| **HITL-P07** | `OP_AUTH_ESCALATION` | Requerimiento de múltiples firmas. | Impacto > Threshold. | Bloqueo de Quorum N/3 HitL. | Indefinida | P0 | Múltiples operadores firman. |
| **HITL-P08** | `OP_MOCK_APPROVAL` | Bypass seguro para simulación. | `ENV_MOCK == True`. | Log de Auto-Aprobación. | O(1) | P2 | Ejecución local de tests. |
| **HITL-P09** | `OP_HUMAN_OVERRIDE` | Inyección de entropía humana forzada. | Edición manual del payload en UI. | Delta entre Payload original y final. | Segundos | P1 | Actualización del Hash Taint. |
| **HITL-P10** | `OP_STATE_FREEZE` | Cierre a solo-lectura de la BD. | Inicio de evaluación HitL. | Lock WAL DB en `READ_ONLY`. | MS | P0 | Bloqueo de mutación de fondo. |

## MATRIZ 2: INVARIANTES TERMODINÁMICAS (1-10)
| ID | Invariante HitL | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **HITL-I01** | `INV_DEMIURGE_LOCK` | La máquina propone, el humano dispone. | Ningún `INSERT/UPDATE` sin ED25519. | Auto-firma agentica detectada. | `sig == FALSE` rechaza. |
| **HITL-I02** | `INV_ZERO_ATP_SEARCH` | La fase de búsqueda no interrumpe al humano. | El enjambre no pide ayuda técnica. | Agente en bucle infinito. | Interrupciones / H == 0. |
| **HITL-I03** | `INV_ASYNC_GATE` | El bloqueo HitL no paraliza a otros agentes. | Uso estricto de Futures/Promises. | Event Loop bloqueado (GIL). | Latencia otros agentes == 0. |
| **HITL-I04** | `INV_TAINT_MATCH` | El hash aprobado debe coincidir con el payload exacto. | Cualquier alteración bit a bit invalida. | Mitm o re-escritura post-firma. | `hash(payload) == approved_hash`. |
| **HITL-I05** | `INV_NO_PROSE_GATE` | La aprobación es binaria y estructural. | Sin explicaciones LLM en el prompt HitL. | Exceso de tokens en la UI. | Bytes de UI < 1024. |
| **HITL-I06** | `INV_SILENT_DISCARD` | El rechazo humano no genera debate. | Agente acepta rechazo atómicamente. | LLM pregunta "¿Por qué?". | Anergía == 0. |
| **HITL-I07** | `INV_AUDIT_TRAIL` | Toda aprobación se escribe en el Ledger. | Cadena inmutable de responsabilidad. | Base de datos corrompida. | `Ledger.verify()` == True. |
| **HITL-I08** | `INV_ISOLATED_SANDBOX` | El código a aprobar debe ser reproducible off-chain. | HitL evalúa tests, no promesas. | Código sin suite de pruebas. | `pytest exit_code == 0`. |
| **HITL-I09** | `INV_VOLATILE_ARTIFACT` | Si el humano no firma, el artefacto se degrada. | Expulsión LFU para evitar State Bloat. | RAM/Disco llena de pending_tasks. | `TTL < 48h`. |
| **HITL-I10** | `INV_CRITICAL_CONTEXT` | La alerta HitL incluye el Radio de Blast (Riesgo). | El humano asume la entropía exacta. | Aprobación ciega (Blind Sign). | `risk_level` explicitado. |
