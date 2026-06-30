# ONTOLOGY-FORGE-OMEGA: INFORMATION THEORY & ENTROPY COMPACTION (BATCH 1)
**Dominio:** Teoría de la Información, Compresión Termodinámica, Entropía de Shannon y Límites de Landauer
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 20 PRIMITIVAS DE COLAPSO (INF-P01..20)
Mecanismos elementales de degradación informativa, ruido y saturación del espacio de estados.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **INF-P01** | `OP_ENTROPY_DILUTION`| Descenso abrupto en la entropía por redundancia conversacional (slop). | Ingesta de texto repetitivo o adornos lingüísticos. | Entropía de Shannon < 1.5 bits/carácter. | MS | P1 | Filtrar mediante ExergyGuard (Ω13). |
| **INF-P02** | `OP_CONTEXT_OVERFLOW`| Pérdida de estado debido a truncado del prompt window del LLM. | Tamaño del buffer de entrada supera límite del token context. | Truncamiento silencioso o error de API. | MS | P0 | Invocar Thermodynamic-Context-Compression-OMEGA. |
| **INF-P03** | `OP_ERASURE_STALL` | Bloqueo por borrado masivo de celdas de memoria en base de datos. | Apoptosis masiva de workers o purga del Vault. | Latencia de escritura WAL > 5000ms. | O(N) | P1 | Ejecutar borrado asíncrono segmentado por sub-lotes. |
| **INF-P04** | `OP_COMPRESS_FAIL` | Pérdida de señal funcional tras minificación agresiva del AST. | Eliminación de tokens sintácticos críticos en el compresor. | SyntaxError al re-importar el código compactado. | O(1) | P0 | Deshacer compresión y restaurar rama mediante Git Sentinel. |
| **INF-P05** | `OP_META_STRIPPING` | Pérdida de procedencia por mapeado incorrecto de metadatos JSON. | Serialización intermedia sin encapsulado de tipos. | Campo `CORTEX-TAINT` ausente en el payload. | MS | P0 | Abortar transacción SAGA e invalidar inserción. |
| **INF-P06** | `OP_EMBEDDING_DRIFT` | Desviación decimal en la distancia vectorial de embeddings locales. | Carga de modelo ONNX incorrecto o truncado de precisión. | False Positive rate > 40% en búsquedas RAG. | Segundos | P1 | Recargar modelo original y verificar hash SHA-256. |
| **INF-P07** | `OP_RAG_COLLISION` | Recuperación de contexto irrelevante debido a vectores colisionados. | Dimensionamiento incorrecto del vector space. | Distancia coseno a distractor ≈ 0.0. | <5ms | P2 | Re-indexación con tabla virtual vec0 segregada. |
| **INF-P08** | `OP_CONTEXT_ROT` | Degradación acumulativa de la precisión causal en contextos largos. | Ingesta de historial no comprimido en prompts recurrentes. | Alucinación paramétrica en respuestas del enjambre. | Horas | P1 | Purga forzada y compresión mediante LandauerGuard (Ω₄). |
| **INF-P09** | `OP_DUPLICATE_INSERT`| Duplicidad lógica de hechos en la base vectorial del enjambre. | Ausencia de capa de deduplicación previa. | Tamaño de base de datos crece de forma no lineal. | O(N) | P2 | Cargar filtro Bloom pre-inserción. |
| **INF-P10** | `OP_COMPLEXITY_SPIKE`| Incremento masivo de complejidad en ficheros de configuración. | Adición incremental de heurísticas de control redundantes. | Dificultad de parsing / Tiempos de compilación largos. | Continua | P2 | Purga LEA-OMEGA de propiedades redundantes. |
| **INF-P11** | `OP_PRUNE_ERROR` | Eliminación accidental de hechos inmutables durante purgas LFU. | Algoritmo de limpieza confunde invariantes con datos efímeros. | Falla de consistencia en el Master Ledger. | MS | P0 | Bloquear purgas en tablas marcadas como `sacred`. |
| **INF-P12** | `OP_JITTER_SPIKE` | Inestabilidad en la tasa de latencia de ejecución del bus. | Competencia por GIL o congestión de hilos asyncio. | Desviación estándar del loop time > 50ms. | Segundos | P1 | Forzar await asyncio.sleep(0) para ceder control. |
| **INF-P13** | `OP_NULL_PAYLOAD` | Transmisión de buffers vacíos a través del bus de eventos. | Error de inicialización en emisor de señales. | `ValueError: empty payload` en log. | <10ms | P2 | Validar payload no vacío en guard de entrada del bus. |
| **INF-P14** | `OP_TAINT_DECAY` | Pérdida de procedencia por manipulación de cadenas en el worker. | Limpieza de caracteres no ascii borra metadatos. | Hash del Taint corrupto. | O(1) | P0 | SAGA rollback. |
| **INF-P15** | `OP_BUFFER_OVERFLOW` | Desbordamiento de buffer al procesar respuestas JSON masivas. | Falta de límite en tamaño máximo de lectura del API client. | OOM crash de la corrutina de red. | Segundos | P0 | Limitar payload size a 10MB en HTTP middleware. |
| **INF-P16** | `OP_FLOAT_ROUNDING` | Desviación de precisión al serializar floats a formato de texto. | Guardar pesos vectoriales sin truncado matemático explícito. | Pérdida de precisión de distancia de similitud. | O(1) | P2 | Usar formato decimal de precisión fija. |
| **INF-P17** | `OP_DEADLOCK_BUS` | Bloqueo mutuo en el acceso síncrono al bus de mensajes. | Nodos concurrentes escriben sin usar locks. | Suspensión indefinida de corrutinas del Swarm. | Segundos | P0 | WAL Mode y busy_timeout=5000ms. |
| **INF-P18** | `OP_VEC_OOM` | Agotamiento de RAM en el cálculo de embeddings vectoriales locales. | Lote de texto de entrada excede tamaño de bloque del ONNX. | Proceso del SO mata la app con señal SIGKILL. | Segundos | P0 | Segmentación estricta de batches a 32 chunks máximo. |
| **INF-P19** | `OP_VOCAB_MISMATCH` | Mapeo incorrecto de tokens en el vector space. | Actualización del modelo local sin actualizar tokenizador. | Texto decodificado incomprensible (caracteres basura). | Continua | P0 | Validar versión de tokenizador en bootstrap. |
| **INF-P20** | `OP_UNICODE_DECODE` | Crash al procesar caracteres UTF-8 inválidos en payloads. | Ingesta de bytes binarios directos sin encoding. | `UnicodeDecodeError` aborta la lectura del archivo. | MS | P2 | Forzar lectura con error handling `replace/ignore`. |

## MATRIZ 2: 20 INVARIANTES TERMODINÁMICAS (INF-I01..20)
Leyes de conservación y disipación de flujos de información en el sistema.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **INF-I01** | `INV_SHANNON_FLOOR` | Toda traza de log debe superar el 80% de densidad informativa real. | Erradicación del Green Theater. | Logs de debug redundantes. | `Entropy(Log) >= Threshold`. |
| **INF-I02** | `INV_GC_ISOLATION` | La apoptosis física de workers libera memoria RAM a nivel del sistema operativo. | Evita fugas acumulativas de memoria. | Worker finalizado. | `Processes_Active == 0`. |
| **INF-I03** | `INV_COMPRESS_LIMIT` | Toda compactación conserva los puntos de entrada y salida del AST del código. | Preserva funcionalidad lógica. | Optimización de código. | `AST_Interface(t1) == AST_Interface(t0)`. |
| **INF-I04** | `INV_CONTEXT_CAP` | La saturación del prompt window está acotada estrictamente al 85%. | Previene truncados silenciosos. | Prompt compilado. | `Token_Count < max_tokens * 0.85`. |
| **INF-I05** | `INV_DETERMINISTIC_SER`| La serialización JSON de diccionarios de estado usa claves ordenadas. | Consistencia de firma de hash. | Guardado en Ledger. | `json.dumps(obj, sort_keys=True)`. |
| **INF-I06** | `INV_COSINE_METRIC` | Las distancias vectoriales se calculan exclusivamente mediante coseno. | Uniformidad de similitud semántica. | Comparación RAG. | `Metric == Cosine`. |
| **INF-I07** | `INV_SCHEMA_CHECK` | Todo payload serializado pasa validación estricta de tipo en el guard. | Prevención de tipos corruptos. | Recepción en puerto. | `jsonschema.validate() == Success`. |
| **INF-I08** | `INV_TOKENIZER_VER` | La versión del modelo ONNX coincide exactamente con el tokenizador local. | Evita colapso del vector space. | Arranque de embedding. | `hash(Model) == hash(Tokenizer_Map)`. |
| **INF-I09** | `INV_FLOAT_PRECISION`| Los pesos de vectores en SQLite se guardan como BLOB binarios FP32. | Evita desbordamiento de conversión. | Escritura en vec0. | `Type(Embedding) == BLOB(float32)`. |
| **INF-I10** | `INV_NON_BLOCKING` | La escritura en bus usa primitivas asyncio no-bloqueantes de la GIL. | Mantiene latencia baja. | Mutación en Event Bus. | `GIL_Blocked == False`. |
| **INF-I11** | `INV_NO_NULL` | No se transmiten payloads vacíos ni nulos en el bus de control. | Evita ciclos de cómputo inútiles. | Despacho de señal. | `len(Signal.payload) > 0`. |
| **INF-I12** | `INV_TAINT_HEADER` | Todo hecho almacenado contiene metadatos del autor y timestamp. | Garantía de procedencia. | Query en fact store. | `contains(taint_id) == True`. |
| **INF-I13** | `INV_UTF8_ENCODING` | Toda lectura y escritura en archivos de texto fuerza codificación UTF-8. | Previene fallos de parsing. | File open call. | `encoding == "utf-8"`. |
| **INF-I14** | `INV_BUFFER_MAX` | El tamaño máximo de lectura de peticiones HTTP es de 10MB. | Prevención de DDoS por memoria. | Conexión entrante de API. | `Content_Length <= 10MB`. |
| **INF-I15** | `INV_DECIMAL_SCALE` | Las puntuaciones y métricas se formatean con un máximo de 4 decimales. | Uniformidad sintáctica. | Output de logs / ledgers. | `Precision(Metric) <= 4`. |
| **INF-I16** | `INV_MUTEX_WAL` | Todo acceso concurrente a base de datos usa modo WAL y mutex único. | Evita deadlocks de persistencia. | Database open connection. | `journal_mode == WAL`. |
| **INF-I17** | `INV_CGROUPS_LIMIT` | Los subagentes corren bajo límites de CPU y memoria estrictos del SO. | Contención contra OOM general. | Spawn de worker. | `Memory_Limit <= 512MB`. |
| **INF-I18** | `INV_STATIC_VOCAB` | Las llaves de indexación vectorial son inmutables durante el ciclo de vida. | Evita desalineación de memoria. | Inserción RAG. | `Vocabulary_Locked == True`. |
| **INF-I19** | `INV_DEDUPLICATION` | No se permiten inserciones vectoriales con distancia coseno superior al 99%. | Evita redundancia acumulativa. | Pre-inserción check. | `max(CosineSimilarity) < 0.99`. |
| **INF-I20** | `INV_LANDAUER_BOUND` | El borrado de 1 bit de información disipa una energía mínima de $kT \ln 2$. | Límite físico de borrado. | Apoptosis del sistema. | `Energy_Spent >= kT_ln2`. |

## MATRIZ 3: 5 ANTIPATRONES ESTOCÁSTICOS (INF-AP01..05)
Fragilidades arquitectónicas en el manejo de entropía e información.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **INF-AP01** | **Verbose Logging** | Escribir trazas masivas de texto plano sin valor de verdad ni firmas criptográficas. | Tamaño de fichero log > 1GB / logs repetidos. | Caída del rendimiento I/O de disco. | Filtrado por entropía mínima (INV_SHANNON_FLOOR). |
| **INF-AP02** | **Dynamic Vocabularies**| Modificar el conjunto de caracteres o modelo del tokenizador en caliente. | Errores de descodificación semántica. | Ruina del espacio vectorial RAG. | Clases de tokenizador inmutables y estáticas. |
| **INF-AP03** | **String Vector Storage**| Almacenar arrays de floats como strings formateados de texto en SQLite. | Filas SQLite con texto `"0.123,0.456,..."`. | Ineficiencia de lectura y truncado de precisión. | Guardar en BLOB binario float32 nativo. |
| **INF-AP04** | **Bare Bytes Ingest** | Leer ficheros sin especificar encoding asumiendo codificación del sistema. | Fallos aleatorios de UnicodeDecode en distintos hosts. | Inestabilidad multiplataforma. | Forzar UTF-8 explícito en cada apertura. |
| **INF-AP05** | **Infinite Context Pile**| Acumular historial en bruto en el prompt sin aplicar compresión ni resúmenes. | Latencia TTFT crece linealmente / Context overflow. | Desplome de la eficiencia exérgica del LLM. | Compresión termodinámica periódica. |

## MATRIZ 4: 3 REDUNDANCIAS ACTIVAS (INF-RA01..03)
Mecanismos de respaldo para flujos de datos.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **INF-RA01** | **Dual Model Backups** | Copia redundante del archivo del modelo local ONNX en directorio read-only. | Corrupción accidental del fichero binario. | 50MB espacio disco. | `cortex/embeddings/` |
| **INF-RA02** | **Parallel Tokenization**| Doble validación de tokens codificados/decodificados antes de inferencia. | Desincronización del vocabulario del host. | Tiempo de cálculo despreciable. | `sentence-transformers` |
| **INF-RA03** | **Compress Fallback** | Doble motor de compactación de historial (Resumen semántico + Compresión zip). | Fallo de lógica de minificación en buffers. | Latencia adicional de CPU en fallbacks. | `cortex/compaction/` |

## MATRIZ 5: 5 VECTORES DE ATAQUE ADVERSARIAL (INF-AV01..05)
Técnicas de inyección de caos y envenenamiento informativo.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **INF-AV01** | **Semantic Dilution** | Prompt window / logs de entrada. | Inyección de grandes bloques de texto con alta entropía pero nulo valor de verdad. | Colapso del ratio exergético (Anergía++). | ExergyGuard (Ω13) y colapso de contexto. |
| **INF-AV02** | **Vector Manipulation** | Búsqueda semántica RAG. | Insertar vectores calculados para forzar colisión con llaves críticas. | Falsa recuperación en consultas de seguridad. | Verificación SHA-256 de base de datos vec0. |
| **INF-AV03** | **Context Overflow DOS**| Endpoint público de API. | Peticiones con payloads gigantes para agotar RAM en embeddings. | Invocación de OOM del SO (SIGKILL). | Limitación estricta de buffer (INV_BUFFER_MAX). |
| **INF-AV04** | **Tokenizer Crash** | Entrada de caracteres unicode exóticos. | Envío de secuencias diseñadas para crasear el tokenizador. | Excepción no controlada que aborta el hilo. | Encoding Unicode con ignore de caracteres rotos. |
| **INF-AV05** | **Memory Harvesting** | Ficheros temporales del sistema. | Lectura de volcados de memoria `/tmp/` no borrados. | Extracción de historial del contexto. | Borrado asíncrono obligatorio (INV_GC_ISOLATION). |
