# ONTOLOGY-FORGE-OMEGA: MATRIZ HITL (BATCH 3)
**Dominio:** Human-in-the-Loop (HitL) / Autorización Asimétrica
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: PRIMITIVAS DE COLAPSO (21-30)
| ID | Primitiva HitL | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **HITL-P21** | `OP_RATIONALE_EXTRACT` | Extracción forzada del motivo de rechazo. | Humano pulsa "Rechazar". | Prompt modal (Opcional). | Segundos | P2 | Inyección de nuevo contexto al LLM. |
| **HITL-P22** | `OP_MULTI_TENANT_SIGN` | Exigir firmas de distintos dominios. | Mutación afecta > 1 tenant. | Bloqueo cruzado de Tenant. | Indefinida | P0 | Aprobación concurrente. |
| **HITL-P23** | `OP_REVERT_PROMPT` | Oferta rápida de Rollback post-firma. | Primeros 5s tras "Aprobar". | Mutex temporal de arrepentimiento. | 5s | P1 | Cancela emisión final. |
| **HITL-P24** | `OP_VISUAL_SPOOF_DEF` | Prevenir homógrafos en el UI HitL. | Render de caracteres confusos. | Escáner Unicode alerta. | O(N) | P0 | Reemplaza con ASCII estándar. |
| **HITL-P25** | `OP_BIOMETRIC_PROXY` | Aserción hardware (TouchID/YubiKey). | Operación P0 Ultra-Crítica. | Requerimiento WebAuthn. | MS | P0 | Cierre de circuito de hardware. |
| **HITL-P26** | `OP_HEURISTIC_PREAPPROVE`| Pre-firma probabilística en riesgo nulo. | `Risk == LOW && PPI == 5`. | Aprobación sombra (Shadow). | O(1) | P2 | Auditable post-facto. |
| **HITL-P27** | `OP_HUMAN_AMNESIA` | Agente olvida intentos previos rechazados. | Rechazo HitL + Flag `HARD_RESET`. | Purga de Vector DB local. | MS | P0 | Reinicio termodinámico total. |
| **HITL-P28** | `OP_SYNTHETIC_CHALLENGE`| Agente inyecta un falso positivo para test. | Auditar atención del Demiurgo. | Propuesta deliberadamente mala. | Aleatoria | P1 | Evalúa Fatiga HitL. |
| **HITL-P29** | `OP_LOCKOUT_PENALTY` | Penalización temporal tras N rechazos. | $> 3$ rechazos consecutivos. | Suspensión del Worker (Sleep). | Horas | P2 | Evita DDoS atencional. |
| **HITL-P30** | `OP_FINAL_ATTESTATION` | Sellado final inmutable post-ejecución. | Saga completado con HitL. | Emisión de PDF/Markdown firmado. | O(N) | P1 | Registro forense off-chain. |

## MATRIZ 2: INVARIANTES TERMODINÁMICAS (21-30)
| ID | Invariante HitL | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **HITL-I21** | `INV_FALSE_POSITIVE_CAP`| Límite térmico de alertas basura. | Si el sistema propone demasiados falsos P0, el humano colapsa. | `Reject_Rate > 80%`. | Ajuste de Temp LLM obligado. |
| **HITL-I22** | `INV_IRREVERSIBILITY_TAG`| Si el SAGA-N no tiene rollback, la alerta HitL debe ser Roja. | Obliga a diferenciar riesgo. | Operación destructiva sin TAG. | `Tag(Irreversible) == True`. |
| **HITL-I23** | `INV_TRUST_DECAY` | La confianza en la inferencia decae sin feedback humano. | Forzar HitL esporádico incluso en flujos seguros. | Tiempo sin HitL > 7 días. | Alerta de calibración. |
| **HITL-I24** | `INV_CONTEXT_PRESERVATION`| La memoria RAM del agente no muere por timeout de HitL. | Persistir la pila de llamadas a disco. | HitL expirado = Pérdida de estado. | `RAM_Dump_Exists == True`. |
| **HITL-I25** | `INV_SYBIL_RESISTANCE` | El agente no puede suplantar al Operador (No Self-Sign). | Separación estricta de Roles OS/Keys. | `Agent_Role == Demiurge`. | Violación P0 (Apoptosis). |
| **HITL-I26** | `INV_NO_DEFERRED_SIGN` | La firma debe darse en el momento del renderizado del estado. | Evita el exploit Time-of-Check to Time-of-Use (TOCTOU). | Estado mutó en BD mientras HitL pendía. | `hash_t0 == hash_t1`. |
| **HITL-I27** | `INV_BLAST_RADIUS_EXPLICIT`| El radio de impacto (Blast Radius) debe ser calculable en O(1). | HitL exige conocer qué se destruye. | `BlastRadius() == Undefined`. | Transacción abortada. |
| **HITL-I28** | `INV_HUMAN_STOCHASTICS` | El input humano es intrínsecamente estocástico (con errores). | El sistema debe filtrar typos (INV_IGNORE_TYPOS). | Fallo estructural por un typo. | `Input_Sanitization == True`. |
| **HITL-I29** | `INV_ZERO_KNOWLEDGE_GATE`| El humano puede firmar probando conocimiento sin revelar la llave. | Integración con ZK-SNARKs o Vaults OS-native. | Llave expuesta en memoria cruda. | `Key_in_RAM == False`. |
| **HITL-I30** | `INV_PHYSICAL_OVERRIDE` | Un "Botón de Pánico" físico desautoriza cualquier Swarm. | Conexión directa OS (SIGKILL masivo). | Swarm ignora HitL abort. | `Worker_Count == 0`. |
