# ONTOLOGY-FORGE-OMEGA: SWARM CONSENSUS & BFT (BATCH 1)
**Dominio:** Tolerancia a Fallas Bizantinas (BFT), Consenso Distribuidor y Alineación de Enjambres
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 15 PRIMITIVAS DE COLAPSO (BFT-P01..15)
Mecanismos elementales de desviación, latencia y corrupción en el consenso del enjambre.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **BFT-P01** | `OP_QUORUM_DRIFT` | Desviación gradual en las aserciones de los nodos debido a diferencias en logits de temperatura. | Variación en carga térmica de GPUs. | Divergencia > 20% en veredictos semánticos. | O(N) | P1 | Forzar temperatura basal T=0.0 en el enjambre. |
| **BFT-P02** | `OP_SPLIT_BRAIN` | Partición lógica donde dos sub-enjambres aprueban de manera independiente y contradictoria. | Falla de conexión en el socket IPC / bus. | Multi-alerta de mutación en la misma proposición. | <500ms | P0 | Re-congelamiento de bases de datos mediante OP_WAL_LOCK. |
| **BFT-P03** | `OP_VETO_SATURATE` | Bloqueo intencionado de transacciones SAGA mediante inyección masiva de votos negativos. | Un nodo comprometido o sensor drift extremo. | Tasa de rechazo transaccional > 66%. | MS | P0 | Degradación de peso del nodo e invocación de OP_PUNISH_NODE. |
| **BFT-P04** | `OP_BYZANTINE_LIE` | Emisión de resultados falsificados pero criptográficamente firmados. | Nodo con llave válida pero lógica comprometida. | Falla en test de aserción post-persistencia. | O(1) | P0 | Slashing epistémico inmediato y revocación de identidad. |
| **BFT-P05** | `OP_DELAY_POISON` | Inyección de latencia artificial para descalibrar el sincronismo del enjambre. | Retraso intencionado en el retorno de tool calls. | TTFT excede threshold crítico de 3s. | Segundos | P1 | Aborto y re-enrutamiento automático a canal redundante. |
| **BFT-P06** | `OP_SYBIL_INFLATE` | Creación de identidades virtuales efímeras para copar el quórum. | Falla en validación de registro central. | Incremento anómalo en la cola de registro de nodos. | Minutos | P0 | Bloqueo de registro y exigencia de TouchID/TouchKey. |
| **BFT-P07** | `OP_GOSSIP_FLOOD` | Saturación del bus de eventos mediante emisión infinita de mensajes de control. | Bucle infinito en heurísticas de subagentes. | CPU usage al 100% / Cola de red saturada. | MS | P0 | SIGKILL atómico al emisor y regeneración de bus. |
| **BFT-P08** | `OP_EVIDENCE_WIPE` | Intento de borrar el linaje causal del ledger alterando el historial de commits. | Agente intenta usar force push en el DAG. | Desviación entre el hash del ledger y la punta del commit. | O(N) | P0 | Lockout permanente del agente y restauración desde snapshot. |
| **BFT-P09** | `OP_REPLAY_INJECT` | Reinyección de señales de voto pasadas para duplicar transacciones de exergía. | Ausencia de salt/nonce temporal en payload. | DuplicateKey error en tabla de auditoría. | <10ms | P1 | Taint binding estricto con timestamp UTC obligatorio. |
| **BFT-P10** | `OP_PROMETHEUS_LEAK` | Exposición accidental de credenciales durante la sincronización de ramas. | Commits que contienen texto plano sensible en diffs. | Scanner de expresión regular activa rechazo. | O(1) | P0 | Rotación inmediata de llaves y re-escritura del DAG Git. |
| **BFT-P11** | `OP_ISOLATE_TIMEOUT` | Muerte por aislamiento de un worker que queda incomunicado durante el consenso. | Caída de red local o bloqueo de cgroup. | Ausencia de latido (heartbeat) > 5s. | O(1) | P2 | Apoptosis de worker y spawn de réplica limpia. |
| **BFT-P12** | `OP_SOFTMAX_COLLAPSE` | Degradación matemática del scoring debido a pesos normalizados a cero. | Distancia vectorial idéntica en distractor. | Inferencia retorna NaNs en el softmax. | MS | P1 | Inyección de jitter estocástico mínimo para romper la simetría. |
| **BFT-P13** | `OP_VRAM_LOCKOUT` | Bloqueo de memoria de video durante inferencias masivas concurrentes. | Invocación de múltiples modelos pesados. | CudaOutOfMemoryException en logs. | Segundos | P0 | OP_VRAM_FLUSH y limitación por cgroups. |
| **BFT-P14** | `OP_MAESTRO_REJECT` | Desautorización del sistema operativo anfitrión ante llamadas no firmadas. | macOS Sandbox Gatekeeper activo. | OperationNotPermitted exception. | MS | P0 | Derivación forzosa a Mac-Control-Ω nativo. |
| **BFT-P15** | `OP_TAINT_DECAY` | Pérdida de procedencia por stripping accidental de metadatos en conversores. | Serialización intermedia sin encapsulado JSON-LD. | Payload carece del prefijo CORTEX-TAINT. | O(1) | P0 | SAGA-1 abort. |

## MATRIZ 2: 15 INVARIANTES TERMODINÁMICAS (BFT-I01..15)
Leyes del consenso distributivo y preservación de la señal útil en el enjambre.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **BFT-I01** | `INV_BFT_CONSENSUS` | Ninguna mutación se consolida sin acuerdo de $2f + 1$ nodos limpios. | Blindaje contra mentiras bizantinas. | $N_{nodos} < 3$. | `votes >= (2f + 1)`. |
| **BFT-I02** | `INV_NO_SELF_APPROVE` | Ningún agente autoriza transacciones que él mismo propuso. | Evita el auto-consenso circular. | Operación SAGA en curso. | `proposer_id != authorizer_id`. |
| **BFT-I03** | `INV_LEDGER_IMMUTABILITY` | Todo registro en el ledger es de tipo append-only e inmutable. | Historial forense incorruptible. | Intento de re-write o truncado. | `git diff --stat == 0` tras push. |
| **BFT-I04** | `INV_TAINT_PROPAGATION` | Cualquier derivación hereda el taint del origen. | Trazabilidad total del linaje. | Operación de transformación de datos. | `taint_out == taint_in`. |
| **BFT-I05** | `INV_CLOCK_LOGICAL` | El orden temporal se rige por vector lógico, no por reloj físico. | Resiliencia ante drift de reloj del SO. | Desincronización horaria entre nodos. | `LogicalVector(t2) > LogicalVector(t1)`. |
| **BFT-I06** | `INV_MONOTONIC_TRUST` | La confianza disminuye ante anomalías y solo aumenta con aserciones. | Prevención de elevaciones de confianza ciegas. | Falla de aserción detectada. | `trust_t2 <= trust_t1`. |
| **BFT-I07** | `INV_ZERO_RECOMPUTE` | Los resultados deterministas se cachean; prohibido re-computar. | Máxima eficiencia de tokens (exergía). | Reingesta de prompt idéntico. | `Cache_Hits == 100%`. |
| **BFT-I08** | `INV_ISOLATED_ENVIRONMENT` | El enjambre corre en sandbox sin comunicación externa no explícita. | Contención contra exfiltración de API keys. | Proceso del Swarm inicia conexión WAN. | `Allowed_Ports(WAN) == 0`. |
| **BFT-I09** | `INV_FORCE_ROLLBACK` | Cualquier inconsistencia menor en el SMT aborta el lote completo. | Mantiene la base de verdad limpia. | Falla en verificación de hoja del árbol Merkle. | `verify_tree() == False -> Abort`. |
| **BFT-I10** | `INV_DEMIURGE_OVERRIDE` | La firma manual del Demiurgo anula cualquier regla distributiva del Swarm. | Soberanía total del Operador. | Conflicto entre agentes y operador. | `Signature(borjamoskv) == Override`. |
| **BFT-I11** | `INV_NO_BLOCKING_IO` | Toda comunicación del enjambre es estrictamente no-bloqueante. | Evita el congelamiento del Event Loop. | Llamada I/O síncrona en hilo principal. | `GIL_Blocked == False`. |
| **BFT-I12** | `INV_CLEAN_SHUTDOWN` | La apoptosis destruye los procesos worker y limpia la RAM efímera. | Evita filtración forense. | Comando de kill ejecutado. | `Processes_Active == 0`. |
| **BFT-I13** | `INV_SHANNON_FLOOR` | La señal útil de los logs debe superar el 80% de densidad informativa. | Erradicación de logs estocásticos ruidosos. | Generación de traza de debug. | `Entropy(Log) >= Threshold`. |
| **BFT-I14** | `INV_WAL_WALKING` | SQLite WAL activo en toda lectura/escritura concurrente. | Evita bloqueos de persistencia en disco. | Conexión de base de datos inicializada. | `journal_mode == WAL`. |
| **BFT-I15** | `INV_NEXUS_HOLINESS` | Los enlaces cruzados de repositorios deben ser de lectura exclusiva. | Previene la mutación cruzada accidental. | Intento de escritura en symlink. | `Link_Permissions == READ_ONLY`. |

## MATRIZ 3: 5 ANTIPATRONES ESTOCÁSTICOS (BFT-AP01..05)
Fragilidades lógicas y operativas en el quórum distribuidor.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **BFT-AP01** | **Soft Consensus Overload** | Promediar veredictos semánticos en lugar de aplicar aserciones booleanas estrictas. | Uso de soft labels o distancias flotantes en el consenso. | Inyección silenciosa de anomalías en la DB. | Colapso a aserción binaria rígida (OP_BFT_VOTE). |
| **BFT-AP02** | **LWW Clock Poisoning** | Resolver colisiones usando el último escritor gana (LWW) basado en reloj local. | timestamp_created usado para decidir el estado ganador en base cruzada. | Drift temporal del host destruye causalidad. | Usar Taint Timestamps enlazados al Vector Lógico (OP_MERGE_LATEST). |
| **BFT-AP03** | **Blind Delegation Trust** | Delegar sub-tareas a Level 4 sin monitorear o auditar sus outputs intermedios. | Level 5 agent asume éxito sin ejecutar OP_TAINT_SCAN. | Propagación silenciosa de fallos lógicos a la DB. | Enforce OODA critique phase y aserción de test. |
| **BFT-AP04** | **Unchecked Environment Bleed** | Heredar variables del host en el subprocess runtime del worker. | payload.py lee os.environ sin filtrado previo. | Exfiltración de API keys en logs. | Filtrar a un safe_env mínimo en VesicularRuntime. |
| **BFT-AP05** | **Sync-on-Async Hang** | Llamar código asíncrono usando `asyncio.run` dentro de bucle de eventos activo. | RuntimeError: "Event loop is already running". | Congelamiento completo del proceso supervisor. | Usar tasks concurrentes o await nativo. |

## MATRIZ 4: 3 REDUNDANCIAS ACTIVAS (BFT-RA01..03)
Estructuras de aislamiento de fallas en el enjambre.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **BFT-RA01** | **Dual Event Bus** | Canal in-memory + persistencia SQLite WAL de respaldo. | Pérdida de señales de eventos ante caída del proceso. | Duplicación de escrituras I/O. | `SqliteMessageBus` / `AsyncSignalBus` |
| **BFT-RA02** | **Heartbeat Watchdog** | Monitoreo activo de la salud del loop de consumo desde hilo supervisor separado. | Muerte silenciosa del consumidor de eventos. | CPU Cycle imperceptible. | `_heartbeat_monitor` / `sys.exit` |
| **BFT-RA03** | **Local Embedder Cache** | Almacén in-memory de embeddings locales ONNX para desacople total de red. | Timeouts de API de embeddings externas. | Consumo de RAM (100MB). | `sentence-transformers` / `ONNX` |

## MATRIZ 5: 5 VECTORES DE ATAQUE ADVERSARIAL (BFT-AV01..05)
Técnicas de inyección de caos y colapso de consenso en el enjambre.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **BFT-AV01** | **Semáforo Bizantino** | Bloqueo mutuo de recursos compartidos (SQLite). | Inducción deliberada de escrituras masivas concurrentes. | Deadlock termodinámico de disco (Anergy++). | busy_timeout=5000ms y reintentos con jitter exponencial. |
| **BFT-AV02** | **Inyección de Taint Huérfano** | Interfaz de persistencia (Fact Store). | Inserción de filas simuladas sin token atribución. | Contaminación estructural de dependencias. | Aserción rígida de firma pre-commit en DB. |
| **BFT-AV03** | **Envenenamiento de Vector RAG** | Base vectorial virtual `vec0`. | Inyección de vectores ruidosos diseñados para colisionar. | Desvío semántico de la recuperación RAG. | Tablas virtuales segregadas por modelo. |
| **BFT-AV04** | **Exploit de TOCTOU en HitL** | Aprobación humana de plan. | Alterar el archivo AST en disco justo tras la firma del diff. | Inyección de código malicioso no auditado. | `hash_t0 == hash_t1` estricto antes de escritura. |
| **BFT-AV05** | **Bucle de Autopoiesis Estocástica** | Generación autónoma de código del Agente. | Inducción de auto-refactorización recursiva sin tests. | Consumo masivo de cuota API y OOM. | Kill Criteria AX-047 y aserción de linter local. |
