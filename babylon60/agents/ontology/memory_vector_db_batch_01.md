# ONTOLOGY-FORGE-OMEGA: MEMORY ARCHITECTURES & VECTOR DATABASE OPERATIONS (BATCH 1)
**Dominio:** Motores de Persistencia, Bases de Datos Vectoriales, SQLite-Vec y Cachés L1/L2 en C5-REAL
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 20 PRIMITIVAS DE COLAPSO (MEM-P01..20)
Mecanismos elementales de fallo de persistencia, corrupción de índices y fugas en el vector space.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **MEM-P01** | `OP_LOST_UPDATE` | Pérdida de actualización en tabla virtual vec0 debido a desincronización lógica. | Mutación concurrente sin mutex de escritura. | Diferencia en delta entre metadatos y tabla vectorial. | MS | P0 | Mutex único de escritura y aislamiento WAL. |
| **MEM-P02** | `OP_DIM_MISMATCH` | Error de dimensiones al comparar vectores de distintos modelos de embeddings. | Query de text-1536 ejecutado sobre tabla de visual-768. | `DimensionMismatchException` en ejecución de query. | MS | P0 | Tablas segregadas estrictamente por modelo de embedding. |
| **MEM-P03** | `OP_CONN_LEAK` | Agotamiento de file descriptors por conexiones a base de datos no cerradas. | Falla al cerrar conexiones asíncronas en `finally`. | `OSError: [Errno 24] Too many open files` en logs. | Lenta | P1 | Forzar context manager asíncrono y límites de pool. |
| **MEM-P04** | `OP_ORPHAN_DELETE`| Borrado de fila de metadatos sin borrar el vector correspondiente en la tabla virtual. | Falla de cascada física (vec0 no soporta foreign keys). | Fila huérfana en vec0 sin mapeo en metadatos. | O(N) | P1 | Borrado lógico manual en vec0 coordinado por trigger. |
| **MEM-P05** | `OP_INDEX_CORRUPT`| Desalineación física entre el índice FTS5/Vec y los registros de la DB. | Escritura interrumpida abruptamente por caída de proceso. | Búsquedas semánticas retornan IDs inexistentes. | O(N) | P0 | Reconstrucción automática de índices en el arranque. |
| **MEM-P06** | `OP_RESULT_BLOAT` | Agotamiento de memoria RAM por consultas que retornan miles de filas sin paginación. | Consulta sin cláusula `LIMIT`. | OOM del proceso durante ejecución de query. | Segundos | P1 | Forzar límites estrictos en consultas por configuración. |
| **MEM-P07** | `OP_SCAN_TIMEOUT` | Expiración del tiempo límite de búsqueda en escaneos vectoriales masivos. | Tabla vec0 crece por encima de 10M de registros sin índice HNSW. | `TimeoutError` en corrutina del query. | Segundos | P1 | Habilitar paginación y segmentación de bases de datos. |
| **MEM-P08** | `OP_CACHE_EVICT` | Pérdida de datos calientes en caché L1 debido a política de desalojo errónea. | Lote masivo de peticiones frías expulsa el contexto actual. | Tasa de cache hits disminuye por debajo del 10%. | Minutos | P2 | Política de desalojo LFU con protección de contexto. |
| **MEM-P09** | `OP_EMBED_REDUND` | Cálculo redundante de embeddings para cadenas idénticas. | Ausencia de capa de cacheo de hashes de texto. | Consumo de tokens de embedding se multiplica por N. | O(N) | P2 | Implementar caché L1 in-memory de embeddings calculados. |
| **MEM-P10** | `OP_LOCK_STARVATION`| Bloqueo prolongado de peticiones de lectura debido a transacciones de escritura. | Transacción de escritura no atómica bloquea la DB. | `database is locked` error en corrutinas de lectura. | Segundos | P0 | WAL Mode y reducción de bloques de transacción. |
| **MEM-P11** | `OP_THRESHOLD_DROP`| Pérdida de resultados relevantes debido a umbral de similitud demasiado alto. | Query configurado con threshold de distancia estático. | Búsqueda RAG retorna cero filas (ZeroResult). | MS | P2 | Adaptar threshold dinámicamente según distribución. |
| **MEM-P12** | `OP_NORM_FAILURE` | Falla en similitud coseno por inserción de vector con norma cero (nulo). | Payload de embedding con todos los elementos en cero. | `DivisionByZero` o NaNs en el scoring de distancia. | MS | P1 | Sanitización pre-inserción de vectores. |
| **MEM-P13** | `OP_FK_VIOLATION` | Falla al insertar metadatos debido a violación de clave foránea. | Inserción de hecho con ID de sesión inexistente. | `IntegrityError: FOREIGN KEY constraint failed`. | MS | P0 | Validar existencia de dependencias antes del commit. |
| **MEM-P14** | `OP_STAMPEDE_HIT` | Saturación por peticiones concurrentes calculando la misma clave faltante. | Cache miss concurrente en L1. | Múltiples corrutinas llaman al modelo ONNX para el mismo texto. | MS | P2 | Mutex de cálculo de clave único (Singleflight). |
| **MEM-P15** | `OP_WAL_EXPLOSION` | Crecimiento incontrolado del archivo WAL de SQLite. | Ausencia de checkpoint pasivo o transacciones abiertas infinitas. | Archivo `-wal` en disco ocupa más de 1GB. | Lenta | P1 | Auto-checkpointing periódico mediante PRAGMA. |
| **MEM-P16** | `OP_FILE_CORRUPT` | Corrupción física del archivo de base de datos `.db`. | Caída de tensión o apagado físico durante escritura. | `sqlite3.DatabaseError: file is encrypted or is not a database`.| O(1) | P0 | Restauración de base de datos desde copia de seguridad. |
| **MEM-P17** | `OP_DIRTY_READ` | Lectura de estado inconsistente no comprometido por otra transacción. | Aislamiento configurado en `READ_UNCOMMITTED`. | Lectura retorna datos que luego sufren rollback. | MS | P1 | Forzar aislamiento mínimo `READ_COMMITTED` estricto. |
| **MEM-P18** | `OP_DISK_FULL` | Falla de persistencia por falta de espacio físico en el disco anfitrión. | Escritura en SQLite falla debido a almacenamiento saturado. | `OSError: [Errno 28] No space left on device`. | Segundos | P0 | Alerta preventiva al 95% de almacenamiento y lock temporal. |
| **MEM-P19** | `OP_INDEX_DOWN` | Falla al consultar índice de base de datos debido a tabla bloqueada. | Operación de reconstrucción de índice bloquea lecturas. | Retardo crítico en búsquedas FTS5. | Segundos | P1 | Ejecutar optimización de índices en background threads. |
| **MEM-P20** | `OP_PASS_EXPIRE` | Expiración de clave de cifrado de base de datos en caliente. | Cambio de pass en Keyring no propagado a conexiones abiertas. | `sqlite3.OperationalError: file is not a database` en queries. | MS | P0 | Recargar clave desde Keyring y reiniciar pool de conexiones. |

## MATRIZ 2: 20 INVARIANTES TERMODINÁMICAS (MEM-I01..20)
Leyes absolutas de consistencia, persistencia y control de transacciones en base de datos.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **MEM-I01** | `INV_VEC_DIMENSION` | La dimensión de los vectores en vec0 debe coincidir exactamente con el modelo ONNX. | Evita errores de tipo en tiempo de ejecución. | Inicialización de tablas vectoriales. | `dimension == 1536`. |
| **MEM-I02** | `INV_WAL_MODE` | Toda base de datos SQLite persistente opera con el diario en modo WAL. | Previene bloqueos de lectura/escritura concurrentes. | Apertura de conexión SQLite. | `journal_mode == wal`. |
| **MEM-I03** | `INV_BUSY_TIMEOUT` | Toda conexión de base de datos establece un timeout de espera de 5000ms. | Previene deadlocks infinitos. | Conexión de base de datos activa. | `busy_timeout == 5000`. |
| **MEM-I04** | `INV_ATOMIC_WRITE` | Las inserciones de metadatos y vectores ocurren dentro del mismo bloque transaccional. | Evita huérfanos vectoriales. | Ejecución de persistencia de hecho. | `transaction_active == True`. |
| **MEM-I05** | `INV_PHYSICAL_CASCADE`| La eliminación de metadatos dispara la purga manual del vector correspondiente en vec0. | Evita desalineación de IDs. | Trigger de eliminación activado. | `count(vec0) == count(metadata)`. |
| **MEM-I06** | `INV_TENANT_SCOPE` | Toda consulta de base de datos restringe la visibilidad al tenant_id del caller. | Garantía estricta de aislamiento. | Compilación de query SQL. | `contains("tenant_id = ?") == True`. |
| **MEM-I07** | `INV_CACHE_INVALID` | Cualquier mutación de escritura invalida los registros correspondientes en caché L1. | Evita lecturas sucias en memoria. | Commit transaccional finalizado. | `cache_dirty == False`. |
| **MEM-I08** | `INV_SERIAL_LEDGER` | Las lecturas en `cortex/audit/ledger.py` usan nivel de aislamiento SERIALIZABLE. | Consistencia criptográfica absoluta. | Conexión a la tabla Ledger. | `isolation_level == SERIALIZABLE`. |
| **MEM-I09** | `INV_HASH_CACHE` | El modelo ONNX solo computa embeddings si el hash del texto es un cache miss. | Ahorro masivo de ciclos de CPU (exergía). | Petición de cálculo de embedding. | `hash_exists(Cache) == False`. |
| **MEM-I10** | `INV_VEC_PRENORM` | Todo vector almacenado en vec0 está pre-normalizado a longitud unitaria (norma = 1). | Acelera búsquedas de similitud coseno. | Escritura en vec0. | `abs(norm(vector) - 1.0) < 1e-5`. |
| **MEM-I11** | `INV_MAX_CONNS` | El número máximo de conexiones abiertas simultáneas en el pool es de 50. | Evita agotamiento de file descriptors. | Pool de conexiones inicializado. | `open_connections <= 50`. |
| **MEM-I12** | `INV_WAL_CHECKPOINT` | SQLite ejecuta un checkpoint pasivo cada 1000 páginas escritas en el diario. | Controla el tamaño de disco ocupado. | Escritura de páginas en el diario. | `wal_checkpoint_rate == 1000`. |
| **MEM-I13** | `INV_READ_COMMITTED` | Las lecturas ordinarias operan bajo aislamiento de tipo READ_COMMITTED. | Evita lecturas de rollback intermedios. | Ejecución de consulta SQL general. | `isolation_level == READ_COMMITTED`. |
| **MEM-I14** | `INV_DISK_THRESHOLD` | La base de datos deniega escrituras si el espacio libre en disco es inferior al 5%. | Previene corrupciones catastróficas. | Loop del Daemon de monitorización. | `free_disk_space >= 5%`. |
| **MEM-I15** | `INV_FOREIGN_KEYS` | La validación de claves foráneas está activa en todas las conexiones SQLite. | Garantiza integridad relacional. | Apertura de conexión. | `foreign_keys == ON`. |
| **MEM-I16** | `INV_COSINE_SIM` | La búsqueda semántica usa estrictamente cálculo de distancia coseno nativa. | Consistencia matemática. | Ejecución de query RAG. | `distance_metric == COSINE`. |
| **MEM-I17** | `INV_INDEX_REBUILD` | El índice de búsqueda textual FTS5 se reconstruye tras cada migración de esquema. | Asegura precisión en búsquedas. | Migración finalizada con éxito. | `fts_rebuild_success == True`. |
| **MEM-I18** | `INV_READ_ONLY_REPS` | Las réplicas secundarias de base de datos operan estrictamente en modo lectura. | Previene desviaciones de consistencia. | Inicialización de conexión a réplica. | `read_only_replica == True`. |
| **MEM-I19** | `INV_AES_DB_CIPHER` | Los datos marcados como confidenciales se cifran con AES-256-GCM antes de persistir. | Confidencialidad a nivel físico. | Ingesta al fact store. | `is_encrypted(data) == True`. |
| **MEM-I20** | `INV_PASS_KEYRING` | La contraseña de cifrado de base de datos se lee de forma segura desde el Keyring OS. | Evita exposición de credenciales. | Inicialización de base de datos. | `read_key(Vault) == True`. |

## MATRIZ 3: 5 ANTIPATRONES ESTOCÁSTICOS (MEM-AP01..05)
Fragilidades lógicas de persistencia y malas prácticas en RAG/Vector space.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **MEM-AP01** | **Virtual Foreign Keys** | Intentar declarar foreign keys directas en la tabla virtual `vec0` de SQLite-Vec. | `FOREIGN KEY` declarada en tabla vec0 en script SQL. | Falla de compilación de esquema o borrado huérfano. | Segregar metadatos y vec0, borrar manualmente (OP_ORPHAN_DELETE). |
| **MEM-AP02** | **Unbounded RAG Scans** | Realizar consultas semánticas sin cláusulas de paginación o límites superiores. | Queries vectoriales sin cláusula `LIMIT N`. | Elevación exponencial de latencia y OOM. | Forzar `LIMIT` dinámico adaptativo en queries. |
| **MEM-AP03** | **Unsafe Pool Sharing** | Compartir conexiones de base de datos SQLite entre múltiples hilos síncronos. | `sqlite3.ProgrammingError: SQLite objects created in a thread...`. | Excepciones no controladas y corrupción de transacciones. | Usar `aiosqlite` o bloqueos asíncronos por conexión. |
| **MEM-AP04** | **Serial DB Writes** | Ejecutar escrituras recurrentes de una en una en bucles síncronos de subagentes. | Múltiples `commit()` individuales dentro de un bucle for. | Caída crítica del rendimiento (exergía) por I/O. | Agrupación de inserciones en transacciones por lotes. |
| **MEM-AP05** | **Text Vector Storage** | Guardar arrays de floats como strings planos con comas en campos de texto de SQLite. | Columnas SQLite con texto `"0.123,0.456,..."`. | Ineficiencia de lectura y truncado de precisión. | Guardar en BLOB binario float32 nativo. |

## MATRIZ 4: 3 REDUNDANCIAS ACTIVAS (MEM-RA01..03)
Aislamiento y continuidad en la capa de datos.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **MEM-RA01** | **Memory DB Replica** | Réplica in-memory de solo lectura de hechos calientes y constantes del sistema. | Latencia crítica de disco en consultas repetitivas. | Carga de RAM duplicada (mínima). | `sqlite3` in-memory |
| **MEM-RA02** | **Hourly Backup** | Dump periódico automatizado de la base de datos a un fichero comprimido de respaldo. | Pérdida catastrófica por corrupción de fichero principal. | Espacio en disco (10% por backup). | `sqlite3_backup` API |
| **MEM-RA03** | **Hybrid Indexing** | Búsqueda semántica (vec0) + búsqueda keyword clásica (FTS5) en paralelo. | Respuestas vacías por falta de términos exactos en embeddings. | 1.5x tiempo de query. | `fts5` / `sqlite-vec` |

## MATRIZ 5: 5 VECTORES DE ATAQUE ADVERSARIAL (MEM-AV01..05)
Vectores de intrusión y caos en los datos persistentes del sistema.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **MEM-AV01** | **SQL Injection in RAG**| Filtros de metadatos en consultas semánticas. | Inyectar sentencias SQL maliciosas en campos de texto de entrada. | Pérdida de confidencialidad o borrado de tablas. | Uso estricto de parámetros de consulta preparados (`?`). |
| **MEM-AV02** | **WAL Blowup Attack** | Transacciones concurrentes masivas. | Escribir millones de filas sin comprometer el commit para agotar disco. | Bloqueo total por disco lleno (OP_DISK_FULL). | Límite preventivo de tamaño de WAL y timeouts rígidos. |
| **MEM-AV03** | **Vector Injection** | Base vectorial vec0. | Insertar vectores calculados matemáticamente para forzar falsas colisiones semánticas. | Desvío malicioso de respuestas RAG del enjambre. | Verificación de firmas de procedencia Taint obligatoria. |
| **MEM-AV04** | **Cache Eviction Flood**| Consultas semánticas aleatorias masivas. | Enviar queries diseñadas para generar cache misses constantes en L1. | Consumo masivo de cuota API y degradación de rendimiento. | LFU con protección de contexto caliente (INV_CACHE_INVALID). |
| **MEM-AV05** | **Database Lock DDoS** | SQLite Connection. | Mantener transacciones de escritura abiertas simulando latencia alta. | Bloqueo por timeout de todos los procesos del Swarm. | Cierre automático de conexiones inactivas tras 5s. |
