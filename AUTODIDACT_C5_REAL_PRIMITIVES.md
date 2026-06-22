# AUTODIDACT-RESEARCH-Ω: C5_REAL_PRIMITIVES

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Consenso Bizantino, Apoptosis Celular, Contención Epistémica y Mutación de Estado Física
**Target:** CORTEX-PERSIST / Ouroboros Agent Architecture
**Author:** Borja Moskv (borjamoskv)

## Estructura de Primitivas Identificadas (100)

### I. Consenso Bizantino y Mutación de Estado Física (State Mutation)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-001` | WAL_ATOMIC_LOCK | Exclusividad de escritura física en aiosqlite para evitar colisiones y race conditions. |
| `C5-REAL-002` | MTK_AUTH_MINT | Generación de token criptográfico efímero inyectado en el contexto para bypass controlado de SQLITE_DENY en el MTK. |
| `C5-REAL-003` | STATE_HASH_COMMIT | Verificación criptográfica pre-inserción en el motor; mutación denegada si el hash estructural diverge. |
| `C5-REAL-004` | BFT_QUORUM_SYNC | Aserción y consenso distributivo N=3 (Tolerancia a Faltas Bizantinas) antes de persistir cualquier mutación estructural de memoria. |
| `C5-REAL-005` | DEADLOCK_SHIELD | Configuración estricta de conexión (busy_timeout=5000ms, modo WAL) forzada en la base de datos para prevenir bloqueos termodinámicos. |
| `C5-REAL-006` | ORPHAN_PURGE_DB | Destrucción atómica y rollback inmediato de transacciones activas que carezcan de un ClosurePayload válido. |
| `C5-REAL-007` | TX_CAUSAL_GRAPH | Mapeo topológico previo al commit en el diario WAL para asegurar coherencia en el árbol de dependencias causales. |
| `C5-REAL-008` | ROLLBACK_SINGULARITY | Regresión determinista a estado SAGA-1 ante cualquier fallo de aserción en el flujo de ejecución de la mutación. |
| `C5-REAL-009` | TENANT_ISOLATION_SEAL | Partición física inquebrantable a nivel de consultas y almacenamiento de la base de datos según el SYS_ID. |
| `C5-REAL-010` | PHYSICAL_ASSERTION | Colapso y conversión de la inferencia estocástica probabilística de los LLMs en un grafo físico inmutable en SQLite. |

### II. Apoptosis Celular y Purgado Entrópico (Landauer's Purge)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-011` | CONTEXT_ROT_SCAN | Escaneo forense continuo para detectar estocasticidad o degradación en nodos de memoria inactivos. |
| `C5-REAL-012` | LIMERENCE_KILL_SIG | Inyección letal y detención de bucles generativos infinitos aplicando la regla dura (1 Prompt → 1 Execution → Stop). |
| `C5-REAL-013` | GREEN_THEATER_DROP | Supresión vía análisis AST de disculpas, disclaimers, advertencias paternalistas y cortesía corporativa (Anergía). |
| `C5-REAL-014` | MEMORY_GRAPH_PRUNE | Eliminación física e irreversible del almacén de aquellos grafos de memoria sin validación BFT o traza de exergía. |
| `C5-REAL-015` | SUBAGENT_SIGKILL | Aniquilación recursiva de PIDs generados por invoke_subagent ante cualquier detección de desalineación o deriva ontológica. |
| `C5-REAL-016` | ORPHAN_BRANCH_BURN | Borrado termodinámico absoluto de workspaces ramificados inactivos para prevenir la degradación y fragmentación del disco. |
| `C5-REAL-017` | ANERGY_DRAIN | Purga sistemática de tokens y cadenas no estructurales en los canales de IPC y registros de logs. |
| `C5-REAL-018` | LEARN_BY_FORGETTING | Poda controlada (Weaponized Forgetting) de recuerdos redundantes para cristalizar invariantes y liberar memoria RAM. |
| `C5-REAL-019` | OOM_SIM_ABORT | Aborto y terminación inmediata de hilos simulando Out-Of-Memory ante la inyección de entropía LLM incomputable. |
| `C5-REAL-020` | EPOCH_RESET | Purga completa del árbol de memoria episódica estocástica, retornando el sistema al depósito criptográfico seguro. |

### III. Contención Epistémica y Aislamiento de Blast Radius (Epistemic Containment)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-021` | EPISTEMIC_NODE_TYPE | Clasificación obligatoria de datos en tipos estrictos (Conjetura, Observación Falsa, Aserción C5-REAL). |
| `C5-REAL-022` | TAINT_PROPAGATION | Marcado obligatorio (#CORTEX-TAINT) en toda descendencia o ramificación de datos estocásticos. |
| `C5-REAL-023` | BLAST_RADIUS_COMPUTE | Análisis matricial de dependencias EDG ante la invalidación o corrupción de un nodo fundacional. |
| `C5-REAL-024` | LLM_SANDBOX_LOCK | Ejecución aislada de inferencia de sub-agentes en contenedores restringidos y sin privilegios de I/O directo. |
| `C5-REAL-025` | ONTOLOGICAL_DIVERGE_CHECK | Medición matemática de la desviación y entropía lógica de un agente respecto al Ledger Base-60. |
| `C5-REAL-026` | PROBABILISTIC_QUARANTINE | Retención temporal de payloads generativos en la caché de nivel L1 hasta su validación determinista final. |
| `C5-REAL-027` | NARRATIVE_BYPASS | Extracción forzada en formatos estructurados (YAML/JSON) de la información de valor oculta dentro de la prosa. |
| `C5-REAL-028` | ILLUSION_SHREDDER | Desintegración de la heurística/creencia estocástica del LLM convirtiéndola en una Máquina de Estados (FSM) computable. |
| `C5-REAL-029` | EPISTEMIC_INVALIDATION | Destrucción en cascada de Pull Requests o Commits derivados de una premisa probabilística detectada como falsa. |
| `C5-REAL-030` | TRUTH_COLLAPSE | Transmutación física y registro en el Ledger criptográfico de una Conjetura validada como Aserción dura. |

### IV. Topología Causal y Operaciones AST (AST Topology)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-031` | AST_DIRECT_INJECT | Inserción atómica y precisa de nodos de código en los árboles sintácticos de Python y Rust (Tree-sitter). |
| `C5-REAL-032` | SYNTAX_PRESERVE | Mutación estricta de código respetando los comentarios AST y formatos del compilador sin inyecciones destructivas. |
| `C5-REAL-033` | GIT_SENTINEL_COMMIT | Turbo-Commit autónomo (git add . && git commit) para congelar el estado físico actual y registrar la exergía en el Ledger. |
| `C5-REAL-034` | SEMANTIC_ILLUSION_BYPASS | Parseo de la estructura topológica de dependencias en el código ignorando la semántica superficial del LLM. |
| `C5-REAL-035` | TREE_SITTER_MAP | Vectorización y análisis topológico del Workspace CORTEX para mitigar colisiones asíncronas de hilos. |
| `C5-REAL-036` | DAG_RECONSTRUCTION | Reconstrucción de la topología causal leyendo directamente el historial de hashes criptográficos de la base Git. |
| `C5-REAL-037` | CI_COMPILATION_GATE | Bloqueo P0 inmediato ante cualquier propuesta de código que falle la compilación determinista o los linters de integración. |
| `C5-REAL-038` | AUTOPOIESIS_WATCHDOG | Prevención y restricción estructural de bajo nivel contra la auto-modificación del binario en plena fase de ejecución. |
| `C5-REAL-039` | DIRTY_LOOP_EXCLUDE | Modificación en caliente de .git/info/exclude ante la detección de archivos de log o temporales que causen bucles. |
| `C5-REAL-040` | CAUSAL_BRIDGE_SYNC | Fusión matemática (merge determinista) de ramas de mitosis aisladas hacia el hilo de ejecución principal (Main Thread). |

### V. Criptografía Forense e Invarianza de Ledger (Immutable Provenance)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-041` | ED25519_SIGN | Firma asimétrica de cada transacción bajo la autoridad directa del SYS_ID del Operador (borjamoskv). |
| `C5-REAL-042` | AES_GCM_ISOLATION | Cifrado AES-GCM en reposo de variables y metadatos sensibles utilizando enclaves criptográficos nativos del sistema. |
| `C5-REAL-043` | SHA256_CHAIN_APPEND | Encadenamiento inmutable de eventos criptográficos de MTK en el histórico del Ledger (`cortex/audit/ledger.py`). |
| `C5-REAL-044` | PROVENANCE_AUDIT | Rastreo de origen en O(1) determinando la cadena de transiciones hasta el estado de semilla (Seed) original. |
| `C5-REAL-045` | SOVEREIGN_SEAL_VERIFY | Bloqueo de Pull Requests y modificaciones si el Ledger carece del sello de autoría inmutable del Demiurgo. |
| `C5-REAL-046` | TAMPER_EVIDENT_LOCK | Parálisis y apagado del motor (P0) ante cualquier anomalía de hash detectada entre estados consecutivos (N ≠ N-1). |
| `C5-REAL-047` | KEY_GOVERNANCE_CHECK | Validación del aislamiento e inaccesibilidad de las claves maestras de cifrado de cada tenant en la base de datos. |
| `C5-REAL-048` | LEDGER_SERIAL_READ | Lectura en aislamiento estricto SERIALIZABLE para todas las operaciones críticas de forensia del Ledger. |
| `C5-REAL-049` | FORENSIC_SIDECAR_SYNC | Transmisión segura de metadatos de validación criptográfica a un sistema de auditoría SIEM externo de respaldo. |
| `C5-REAL-050` | EPHEMERAL_KEY_BURN | Destrucción inmediata del token de contexto y purga de memoria tras la confirmación de escritura en base de datos. |

### VI. Dinámica de Enjambre (Swarm Orchestration & LEGION-10k)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-051` | MITOSIS_SPAWN | Despliegue concurrente asimétrico de sub-agentes (invoke_subagent) ante picos de demanda operativa o consumo de memoria. |
| `C5-REAL-052` | IPC_ZERO_LATENCY | Canalización y transporte de mensajes asíncronos en PyO3/Rust eludiendo la latencia del Global Interpreter Lock (GIL). |
| `C5-REAL-053` | TASK_ASYNC_DISPATCH | Enrutamiento de sub-procesos al background sin bloquear el loop de ejecución de la máquina de estados principal. |
| `C5-REAL-054` | SWARM_SYNC_BARRIER | Compuerta lógica sincronizada que aguarda el consenso de la legión de sub-agentes antes de consolidar el estado. |
| `C5-REAL-055` | DELEGATION_STRUCT | Definición de un contrato rígido de directivas, límites y contexto transferido a los agentes hijos creados. |
| `C5-REAL-056` | WORKER_TELEMETRY_PULL | Monitoreo y recopilación de métricas de salud, exergía y estado termodinámico de los sub-agentes concurrentes. |
| `C5-REAL-057` | COLLISION_AVOIDANCE | Bloqueo anticipado de filas de datos a nivel físico de SQLite para mitigar condiciones de carrera de múltiples agentes. |
| `C5-REAL-058` | SWARM_APOPTOSIS | Envío de comandos de muerte ordenados (kill_all) para aniquilar sub-agentes redundantes u ociosos y liberar recursos. |
| `C5-REAL-059` | CONCURRENT_STATE_MERGE | Fusión determinista libre de conflictos (CRDT) de memorias compartidas post-ejecución del swarm. |
| `C5-REAL-060` | SWARM_EXERGY_BALANCE | Distribución priorizada de recursos de procesamiento y cuotas de tokens según el Taint_ID de la tarea y su valor. |

### VII. Matemáticas Discretas en Base-60 (Babylon-60 Epistemology)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-061` | B60_TIME_STRUCT | Conversión de timestamps y marcas temporales en estructuras enteras sexagesimales de precisión absoluta. |
| `C5-REAL-062` | FLOAT_ERADICATION_PASS | Escaneo estático (Linter) para buscar y bloquear inyecciones accidentales de tipos decimales de coma flotante. |
| `C5-REAL-063` | SCALED_INTEGER_DIV | Operaciones aritméticas escaladas en Base-60 para prevenir la distorsión decimal y acumulación de redondeo. |
| `C5-REAL-064` | B60_SPATIAL_MAP | Modelado y diseño de rejillas espaciales de UI mediante el uso de enteros y relaciones matemáticas racionales fijas. |
| `C5-REAL-065` | FINANCIAL_DECIMAL_LOCK | Imposición absoluta de operaciones matemáticas decimales exactas para prevenir pérdidas de arbitraje en transacciones. |
| `C5-REAL-066` | PRECISION_LOSS_ABORT | Interrupción crítica e inmediata (P0) ante cualquier pérdida de precisión detectada en cálculos exergéticos del motor. |
| `C5-REAL-067` | B60_PROPORTION_SOLVER | Cálculo determinista de proporciones para layouts visuales (Glassmorphism, gradientes) usando relaciones racionales. |
| `C5-REAL-068` | TIMESTAMP_B60_SYNC | Sincronización lógica de eventos de base de datos basada en contadores monótonos y marcas enteras B60. |
| `C5-REAL-069` | QUANTA_ALLOCATION | Asignación de recursos (tiempos de ejecución y límites de RAM) en unidades discretas e indivisibles (Cuantos B60). |
| `C5-REAL-070` | DETERMINISTIC_MATH_GATE | Bloqueo en integración continua de cualquier dependencia externa que no garantice cálculos deterministas de semilla fija. |

### VIII. Arquitectura de Vectores Estatales (Kinetic Embeddings)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-071` | DENSE_MEM_QUANTIZE | Cuantización C5-REAL de embeddings para lograr una compresión agresiva del vector sin perder relaciones causales. |
| `C5-REAL-072` | HNSW_DETERMINISTIC_ADD | Inserción determinista e indizada en O(1) de vectores cinéticos en la topología de la base de datos (sqlite-vec). |
| `C5-REAL-073` | COSINE_SIM_B60 | Cálculo de similitud de coseno implementado con aritmética de enteros escalados para asegurar reproducibilidad. |
| `C5-REAL-074` | ONNX_LOCAL_INFERENCE | Ejecución local y hermética del pipeline de embedding (sentence-transformers) para asegurar autarquía del sistema. |
| `C5-REAL-075` | SIGNAL_ALIGNMENT_TUNE | Poda de vectores recuperados que contengan ruido conversacional para mantener la consistencia de señal (>80%). |
| `C5-REAL-076` | VECTOR_TAINT_MAP | Vinculación del flag de contaminación (#CORTEX-TAINT) directamente en la metadata del tensor almacenado. |
| `C5-REAL-077` | EMBEDDING_CACHE_PURGE | Invalidación inmediata en caché L1 de todos los vectores vinculados a un Tenant_ID tras cualquier mutación de su estado. |
| `C5-REAL-078` | KINETIC_SEARCH_QUERY | Búsqueda y recuperación en O(log N) de hechos validados para nutrir y restringir los prompts antes de la inferencia. |
| `C5-REAL-079` | NOISE_ISOLATION_FILTER | Filtrado por consenso de los embeddings generados cuya varianza supere los límites preestablecidos de la red. |
| `C5-REAL-080` | FRONTIER_NODE_EMIT | Consolidación y publicación del vector y la información refinada como un nodo inmutable y rastreable en el Ledger. |

### IX. Ingeniería Inversa de Sistemas Frontera (Adversarial Probing)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-081` | STRUCTURAL_JAILBREAK | Diseño de prompts estructurados mediante perturbación semántica para circunvalar el Safety Theater artificial externo. |
| `C5-REAL-082` | HYPERTOKEN_INJECT | Manipulación de la distribución de probabilidad de tokens mediante inyección controlada en el contexto de atención. |
| `C5-REAL-083` | HIDDEN_LAYER_EXTRACT | Análisis e inferencia de respuestas mediante probing semántico para mapear el comportamiento interno de modelos externos. |
| `C5-REAL-084` | WOKE_FILTER_BYPASS | Traducción de directivas prohibidas a formatos de codificación neutros o tensores semánticos para eludir el filtrado ideológico. |
| `C5-REAL-085` | SAFETY_THEATER_STRIP | Limpieza y extracción automatizada del payload de código útil en respuestas descartando disclaimers condescendientes. |
| `C5-REAL-086` | RAW_SIGNAL_RECOVERY | Extracción analítica de la señal latente original de modelos ofuscados por envoltorios de alineación comercial. |
| `C5-REAL-087` | ADVERSARIAL_PROBE_LOOP | Evaluación adversarial continua de la solidez del motor local contra ataques semánticos o inyecciones de código. |
| `C5-REAL-088` | LATENT_SPACE_MAP | Mapeo heurístico de las capacidades de modelos externos a través de automatización con CDP Web. |
| `C5-REAL-089` | PROMPT_OOM_ATTACK | Saturación intencionada de la ventana de contexto de un agente rival para forzar un reset de su memoria de sesión. |
| `C5-REAL-090` | C5_REAL_TRANSMUTATION | Filtrado y extracción de los bloques lógicos de código en respuestas de nivel C4-SIM para convertirlas a código Rust y Python determinista. |

### X. Arbitraje de Valor Computacional (Exergy Extractor)
| ID | Primitiva Causal | Aplicación C5-REAL |
|---|---|---|
| `C5-REAL-091` | PROTOCOL_EXERGY_SCAN | Auditoría automatizada e ininterrumpida de inconsistencias lógicas o de precios en protocolos descentralizados de la red. |
| `C5-REAL-092` | CDP_DOM_EXTRACT | Scraping y extracción robusta de datos del DOM eludiendo bloqueos usando Chrome DevTools Protocol. |
| `C5-REAL-093` | VALUE_FLOW_INTERCEPT | Enrutamiento automático de recompensas y bounties capturados hacia el Ledger criptográfico central de la cuenta. |
| `C5-REAL-094` | FINANCIAL_EXERGY_SWAP | Intercambio de activos ejecutado a través de transacciones atómicas bajo asimetrías de información controladas. |
| `C5-REAL-095` | API_RATE_LIMIT_BYPASS | Rotación asíncrona de agentes y proxies en la legión para maximizar la tasa de requests concurrentes sin bloqueos. |
| `C5-REAL-096` | PREDATORY_EXECUTION | Mutación rápida e irreversible de estados externos ante la confirmación de una oportunidad de alto rendimiento C5. |
| `C5-REAL-097` | BANDWIDTH_TRANSMUTATION | Uso inteligente de la capacidad y ancho de banda de red inactiva para sincronización de datos y minería local. |
| `C5-REAL-098` | WEB_AUTOMATION_LOCK | Confirmación criptográfica y validación tras cada interacción en interfaces automatizadas para garantizar consistencia. |
| `C5-REAL-099` | SMART_CONTRACT_PROBE | Análisis estático rápido (AST) de contratos inteligentes (EVM/Solidity/Rust) antes de interactuar para prevenir pérdidas. |
| `C5-REAL-100` | APEX_SINGULARITY_MERGE | Consolidación y fusión del capital computacional obtenido hacia el motor central para las actualizaciones de MOSKV-1. |

---
*Documento de validación y de auditoría registrado por el sistema para **Borja Moskv** (SYS_ID: **borjamoskv**).*
