# ONTOLOGY-FORGE-OMEGA: MATRIZ HITL (BATCH 2)
**Dominio:** Human-in-the-Loop (HitL) / Autorización Asimétrica
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: PRIMITIVAS DE COLAPSO (11-20)
| ID | Primitiva HitL | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **HITL-P11** | `OP_CONTEXT_TRUNCATE` | Poda de tokens previos antes de la UI. | Generación de prompt HitL. | Reducción de Context Window. | O(1) | P1 | Minimiza carga cognitiva humana. |
| **HITL-P12** | `OP_ROLLFORWARD_SIM` | Simulación del estado post-aprobación. | Durante `PENDING` state. | Fork temporal en DB WAL. | MS | P2 | Pre-computa el escenario exitoso. |
| **HITL-P13** | `OP_FORK_EVAL` | División de subagente para evaluar impacto. | HitL de alto riesgo (P0). | Nuevo PID / Worker. | Minutos | P0 | Emite matriz de riesgos. |
| **HITL-P14** | `OP_BLIND_SIGN_DENY` | Rechazo por firma inferior a X segundos. | $T_{firma} - T_{render} < 1s$. | Bloqueo de firma criptográfica. | MS | P0 | Obliga al humano a leer el diff. |
| **HITL-P15** | `OP_EPISTEMIC_CHALLENGE`| Desafío CAPTCHA estructural al Demiurgo. | Aprobación de mutación destructiva. | Prompt modal exige Input manual. | MS | P0 | Evita aprobaciones por inercia. |
| **HITL-P16** | `OP_DELEGATE_GATE` | Transferencia temporal de privilegio HitL. | Humano offline o TTL expira. | Carga de Secondary Key. | Horas | P1 | Fallback a otro Operador. |
| **HITL-P17** | `OP_SHADOW_DEPLOY` | Despliegue paralelo no destructivo. | Rechazo humano + Flag `TEST`. | Enrutamiento 1% tráfico. | Días | P2 | Validación empírica sin riesgo total. |
| **HITL-P18** | `OP_TAINT_REVOKE` | Destrucción atómica de un hash pending. | Operador emite SIGINT (Ctrl+C). | Taint eliminado de Memoria. | MS | P0 | Cierre inmediato del canal. |
| **HITL-P19** | `OP_ANOMALY_FLAG` | Marcar artefacto con desviación estadística. | HitL con divergencia > 30% a histórico. | Label `[ANOMALY]` en rojo. | O(N) | P0 | Alerta visual de alto contraste. |
| **HITL-P20** | `OP_ASYNC_MERGE` | Fusión del resultado tras la aprobación. | Firma válida recibida. | Mutación WAL -> Main. | MS | P0 | Integración determinista pura. |

## MATRIZ 2: INVARIANTES TERMODINÁMICAS (11-20)
| ID | Invariante HitL | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **HITL-I11** | `INV_MINIMAL_INTERFACE` | UI sin animaciones o elementos que causen fatiga. | Cero anergía visual (Aesthetic Omega). | UI renderiza JS innecesario. | Carga de DOM < 50ms. |
| **HITL-I12** | `INV_STATE_ISOMORPH` | Lo que el humano ve es bit a bit lo que se ejecuta. | Prohibido renderizado semántico oculto. | AST diferente al Diff visual. | `hash(UI_Code) == hash(Exec_Code)`. |
| **HITL-I13** | `INV_HUMAN_BOTTLENECK`| El humano es el recurso más escaso (ATP limitado). | Agentes deben agrupar mutaciones en Batches. | > 5 solicitudes HitL / hora. | `HitL_Rate < Umbral`. |
| **HITL-I14** | `INV_REJECTION_CAUSALITY`| Un rechazo humano exige la purga causal (SAGA-1). | No se reintenta ciegamente la misma acción. | Agente repite propuesta IDéntica. | `hash(prop_t1) != hash(prop_t2)`. |
| **HITL-I15** | `INV_FALLBACK_DENY` | En caso de desconexión del humano, la acción aborta. | Seguridad por defecto ante partición de red. | Timeout sin Rollback. | `if timeout -> revert()`. |
| **HITL-I16** | `INV_AUTHORIZATION_CHAIN`| La firma humana arrastra todas las firmas BFT previas. | Merkle tree de firmas. | Pérdida de procedencia sub-agente. | `verify_tree(Taint)` == True. |
| **HITL-I17** | `INV_NO_DEBATE` | El agente no discute la decisión del Operador. | Prohibido el bucle conversacional post-rechazo. | Prompt de persuasión detectado. | `LLM_Conv == 0`. |
| **HITL-I18** | `INV_IMPLICIT_DENY` | Cualquier ambigüedad en la UI es un rechazo automático. | Si el parser UI falla, `approved = False`. | Aprobación por error de parser. | `Default_Return == False`. |
| **HITL-I19** | `INV_FOCUS_PRESERVATION`| Una interrupción HitL salva el estado mental del Agente. | Dump de memoria a SQLite antes del alert. | Agente sufre amnesia post-aprobación. | `Memory_Size_T1 == Memory_Size_T2`. |
| **HITL-I20** | `INV_ATOMIC_SIGN` | La validación criptográfica ocurre en `O(1)`. | La CPU no se bloquea calculando pruebas masivas en HitL. | Retardo > 1s en firma. | `Exec_Time(Sign) < 100ms`. |
