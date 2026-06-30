# ONTOLOGY-FORGE-OMEGA: PROCESS ISOLATION & RESOURCE ORCHESTRATION (BATCH 1)
**Dominio:** Aislamiento de Procesos, Membranas Vesiculares, Apoptosis y Orquestación de Cgroups en C5-REAL
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 30 PRIMITIVAS DE COLAPSO (PRC-P01..30)
Mecanismos elementales de fugas de recursos, rupturas de sandbox y fallos de orquestación de procesos.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **PRC-P01** | `OP_WORKER_LEAK` | Fuga de proceso worker que sigue activo tras la parada del supervisor. | Pérdida de referencia PID en el parent. | Proceso python huérfano en background. | Horas | P1 | Enviar SIGKILL mediante OP_APOPTOSIS. |
| **PRC-P02** | `OP_CGROUP_OOM` | El OOM Killer del sistema operativo mata al proceso worker por exceso de memoria. | Inferencia masiva supera límite de cgroups. | Exit code 137 / logs de cgroup out of memory. | <10ms | P0 | Replanificación automática con menor batch. |
| **PRC-P03** | `OP_CPU_STARVE` | Worker acapara ciclos de CPU impidiendo la ejecución de corrutinas supervisoras. | Bucle infinito síncrono sin llamadas de yield. | Latencia del event loop supervisor > 1000ms. | Segundos | P0 | Terminar proceso worker y aislar en cgroup. |
| **PRC-P04** | `OP_THREAD_DEADLOCK`| Bloqueo mutuo entre hilos en el consumidor de colas de eventos. | Dos hilos esperan la liberación del mismo mutex. | Consumo de CPU al 0% con cola de eventos llena. | Indefinida | P0 | Re-inicialización de hilos y locks. |
| **PRC-P05** | `OP_SHM_CORRUPT` | Datos corruptos en el espacio de memoria compartida entre procesos. | Escritura concurrente sin lock de multiprocessing. | `ValueError` o corrupción de datos serializados. | MS | P1 | Re-inicializar buffer compartido. |
| **PRC-P06** | `OP_ZOMBIE_ACUM` | Acumulación de procesos zombies que agotan la tabla de procesos del SO. | El proceso padre no llama a wait() tras la muerte del hijo. | `errno 11: Resource temporarily unavailable`. | Lenta | P1 | Ejecutar waitpid(-1, WNOHANG) periódicamente. |
| **PRC-P07** | `OP_IPC_DISCONNECT` | Pérdida de comunicación en el socket local Unix del bus. | Falla física en el buffer del socket o caída de servicio. | `ConnectionRefusedError` en sockets locales. | MS | P0 | Recreación del socket Unix en `/tmp/`. |
| **PRC-P08** | `OP_PRIORITY_INVERT`| Starvation de tareas críticas debido a procesos de baja prioridad activos. | Configuración de nice incorrecta en subagentes. | Tareas P0 retrasadas mientras tareas P2 avanzan. | Segundos | P2 | Calibración dinámica de nice en cgroups. |
| **PRC-P09** | `OP_ENV_BLEED` | Fuga de credenciales del host hacia la memoria del proceso hijo. | Copia de os.environ sin limpieza previa de keys. | Variables de entorno sensibles accesibles en sandbox. | O(1) | P0 | Forzar safe_env con lista blanca de variables. |
| **PRC-P10** | `OP_SIGNAL_LOSS` | Worker ignora la señal SIGTERM de apagado ordenado. | Captura genérica de señales en el script de inferencia. | Proceso no muere tras 5s de señal SIGTERM. | Segundos | P1 | Escalar a SIGKILL para forzar apoptosis física. |
| **PRC-P11** | `OP_QUOTA_EXHAUST` | Agotamiento del espacio de almacenamiento del scratch sandbox. | Escrituras de logs masivas por subagente comprometido. | `DiskQuotaExceeded` en escrituras de /scratch/. | Segundos | P1 | Limitar escritura por cgroup y cuotas de disco. |
| **PRC-P12** | `OP_FD_LEAK` | Agotamiento de descriptores de archivos al heredar puertos no cerrados. | Spawn de hijo sin activar la bandera close-on-exec. | `Too many open files` en peticiones internas. | Lenta | P1 | Activar flags FD_CLOEXEC en sockets. |
| **PRC-P13** | `OP_FORK_FAIL` | Falla en syscall fork por límites del sistema operativo. | Límite max user processes alcanzado (ulimit -u). | `ForkException` al inicializar worker. | MS | P0 | Reducción de la concurrencia máxima permitida. |
| **PRC-P14** | `OP_INTERP_MISMATCH`| Ejecución con intérprete de Python incorrecto fuera del venv. | Ruta absoluta de binario apunta a Python global del host. | ModuleNotFoundError en importaciones del venv. | O(1) | P0 | Forzar sys.executable para spawn de subprocess. |
| **PRC-P15** | `OP_PROXY_TIMEOUT` | Expiración de tiempo de respuesta de red del proxy local. | Inferencia del proxy local excede el tiempo límite de red. | `h11.RemoteProtocolError` en llamadas internas. | Segundos | P1 | Auto-reinicio de conexión proxy en background. |
| **PRC-P16** | `OP_CHILD_UNHANDLED`| Finalización con código de error del hijo no procesada. | Padre ignora el código de retorno del subprocess. | Inconsistencia de estado post-fallo del subagente. | O(N) | P1 | Replanificación inmediata en caso de return_code != 0. |
| **PRC-P17** | `OP_PERM_CLASH` | Falla al inicializar sandbox por falta de permisos en /tmp/. | Directorio de scratch creado por usuario root previamente. | PermissionError en creación de workspace efímero. | MS | P0 | Generación de UUID único por nombre de workspace. |
| **PRC-P18** | `OP_LAN_BLEED` | Acceso no autorizado de worker a servicios de la red local del host. | Falta de configuración de aislamiento de red en sandbox. | Conexiones de red a IPs locales del host aceptadas. | Segundos | P0 | Aislamiento estricto de red a localhost. |
| **PRC-P19** | `OP_HANDLE_DEADLOCK`| Bloqueo físico de archivos compartidos (DB Lock). | Múltiples subagentes intentan escribir en SQLite sin WAL. | `sqlite3.OperationalError: database is locked`. | Segundos | P0 | PRAGMA busy_timeout=5000 y modo WAL. |
| **PRC-P20** | `OP_SILENT_EXIT` | Finalización silenciosa del worker sin notificar código de salida. | Proceso muere por señal externa SIGKILL de SO. | Desaparición de socket de comunicación sin evento. | MS | P0 | Watchdog comprueba PID activamente cada 500ms. |
| **PRC-P21** | `OP_STACK_OVERFLOW` | Desbordamiento de pila por llamadas recursivas infinitas en subagente. | Heurística recursiva sin control de profundidad máxima. | `RecursionError` en hilo de ejecución. | MS | P1 | Limitar profundidad máxima de recursión a 50. |
| **PRC-P22** | `OP_VERSION_DRIFT` | Ejecución de worker usando código obsoleto cargado en memoria. | Modificación de archivos de script sin reiniciar procesos. | Comportamientos antiguos en ejecuciones activas. | Minutos | P1 | Validar hash SHA-256 de archivos antes del spawn. |
| **PRC-P23** | `OP_CPU_THROTTLE` | Estrangulamiento de velocidad de procesamiento por cuota CPU. | cgroups config de shares CPU al límite. | Retardo masivo en tiempos de respuesta de inferencia. | Continua | P2 | Calibración dinámica de shares según prioridad. |
| **PRC-P24** | `OP_DYLIB_LOAD_FAIL`| Falla en la carga de librerías nativas compartidas (ONNX / CUDA). | Configuración LD_LIBRARY_PATH ausente en safe_env. | `ImportError: libonnxruntime.so` en subprocess. | MS | P0 | Incluir rutas nativas en safe_env PATH. |
| **PRC-P25** | `OP_LOCK_LEAK` | Archivo lock bloquea ejecuciones posteriores tras caída del proceso. | Archivos `.lock` persistidos en disco tras crash. | Nuevos arranques fallan reportando proceso activo. | O(1) | P1 | Comprobar validez de PID guardado en lock file. |
| **PRC-P26** | `OP_PGID_MISMATCH` | Falla al matar grupo de procesos debido a ID de grupo desalineado. | Subprocesos se separan del grupo de procesos del padre. | Workers siguen vivos tras matar proceso supervisor. | MS | P1 | Configurar setpgrp() en spawn de workers. |
| **PRC-P27** | `OP_ROT_WORKER` | Degradación del rendimiento del worker por acumulación de basura en heap. | Ciclos de inferencia acumulados sin recolección de basura. | Incremento constante en el uso de RAM. | Lenta | P1 | Ciclos de recolección de basura GC forzados. |
| **PRC-P28** | `OP_HEAP_LEAK` | Pérdida de memoria en extensiones C de python no liberadas. | Fugas en librerías nativas de ONNX o PyTorch. | Crecimiento incontrolado de memoria residente (RSS). | Lenta | P0 | Apoptosis periódica y regeneración de worker. |
| **PRC-P29** | `OP_PORT_EXHAUST` | Agotamiento de puertos efímeros en llamadas HTTP salientes locales. | Creación continua de sockets sin reutilizar conexiones. | `OSError: Cannot assign requested address`. | Lenta | P1 | Usar pool de sockets HTTP unificados. |
| **PRC-P30** | `OP_ORPHAN_ABORT` | Aborto de worker tras colapso del proceso padre. | Supervisor muere dejando sockets de comunicación colgados. | Worker queda en bucle de lectura sin respuesta de entrada. | MS | P0 | Enviar SIGKILL al worker ante muerte de parent. |

## MATRIZ 2: 30 INVARIANTES TERMODINÁMICAS (PRC-I01..30)
Leyes absolutas de contención de procesos, cuotas de recursos y límites de CPU/RAM.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **PRC-I01** | `INV_CGROUP_LIMIT` | Todo worker se ejecuta en un cgroup con límite máximo de 512MB de RAM. | Previene saturación general de RAM. | Inicialización de subproceso. | `RSS_Usage <= 512MB`. |
| **PRC-I02** | `INV_UNIX_SOCKET` | Las comunicaciones locales de control usan sockets de dominio Unix. | Seguridad por encima de sockets TCP locales. | Enlace de bus local. | `Socket_Type == AF_UNIX`. |
| **PRC-I03** | `INV_SUPERVISOR_PID`| Toda ejecución de subproceso es monitorizada activamente mediante su PID. | Evita procesos huérfanos. | Spawn de worker. | `PID_Exists == True`. |
| **PRC-I04** | `INV_SAFE_ENV_STRIP`| Las variables de entorno de host son purgadas antes del spawn. | Evita fuga de secretos. | Construcción de env. | `len(safe_env) <= 4` (safe_env). |
| **PRC-I05** | `INV_EXEC_TIMEOUT` | La ejecución de payload está acotada estrictamente a un timeout de 15s. | Evita bucles infinitos de CPU. | Inicio de execute(). | `Execution_Time <= 15s`. |
| **PRC-I06** | `INV_APOPTOSIS_KILL`| La apoptosis ante timeout de ejecución usa señal SIGKILL de forma ineludible. | Asegura finalización física. | Expiración de timeout. | `Process_Killed == True`. |
| **PRC-I07** | `INV_VOLATILE_DIR` | El directorio de trabajo del sandbox se destruye al finalizar. | Evita acumulación de basura. | Cierre de VesicularRuntime. | `exists(membrane_path) == False`. |
| **PRC-I08** | `INV_YIELD_OODA` | El loop supervisor cede el control en cada iteración mediante sleep. | Previene starvation de hilos. | Fin de ciclo OODA. | `asyncio.sleep(0) == Executed`. |
| **PRC-I09** | `INV_CPU_LIMIT` | El límite de shares de CPU asignado a los workers es de 50%. | Garantiza CPU libre para el supervisor. | Configuración de cgroups. | `CPU_Shares <= 50%`. |
| **PRC-I10** | `INV_SHM_LOCK` | Toda escritura en memoria compartida se realiza bajo mutex de multiprocessing. | Previene colisión de variables. | Acceso a Value/Array compartido. | `Mutex_Held == True`. |
| **PRC-I11** | `INV_FD_MAX` | El número máximo de descriptores de archivos por subproceso es de 256. | Previene agotamiento de sockets. | Carga de proceso hijo. | `File_Descriptors <= 256`. |
| **PRC-I12** | `INV_REPLAN_FAIL` | Todo fallo de retorno de proceso worker dispara ciclo de replanificación. | Auto-recuperación de fallas. | Worker exit code != 0. | `Replan_Triggered == True`. |
| **PRC-I13** | `INV_WATCHDOG_THREAD`| La salud del Event Loop principal es monitorizada desde un hilo supervisor. | Previene congelamientos del GIL. | Bootstrap de supervisor. | `Watchdog_Alive == True`. |
| **PRC-I14** | `INV_JSON_LOGGING` | Toda traza de log emitida a disco se realiza en formato JSON estructurado. | Facilita parsing automático. | Emisión de traza. | `is_valid_json(Log_Line)`. |
| **PRC-I15** | `INV_TLS_TUNNEL` | Todas las conexiones del enjambre externo pasan por túneles TLS 1.3. | Garantía de transporte. | Handshake de conexión. | `TLS_Version == TLSv1.3`. |
| **PRC-I16** | `INV_UUID_WORKSPACE`| Las rutas temporales de trabajo incorporan UUIDs para evitar colisiones. | Previene sobreescrituras. | Creación de workspace. | `contains_uuid(Path) == True`. |
| **PRC-I17** | `INV_LOCALHOST_ONLY`| Los sockets de red abiertos por el proxy escuchan solo en localhost. | Protección contra ataques LAN. | Binding de red de API. | `Binding_IP == 127.0.0.1`. |
| **PRC-I18** | `INV_CHECKPOINT_FORK`| Los nuevos procesos se clonan a partir de puntos de control estables. | Evita duplicidad de estado sucio. | Spawn de worker. | `Checkpoint_Valid == True`. |
| **PRC-I19** | `INV_VECTOR_CLOCK` | Todo subproceso hereda y actualiza el vector de reloj lógico del padre. | Consistencia cronológica. | Transmisión de mensaje IPC. | `LogicalClock_Hijo >= LogicalClock_Padre`. |
| **PRC-I20** | `INV_NON_ROOT` | Ningún proceso worker se ejecuta con privilegios de root del host. | Privilegio mínimo en sandbox. | Arranque de proceso. | `UID != 0`. |
| **PRC-I21** | `INV_EXIT_CODE_CHECK`| El supervisor evalúa y registra el código de salida de todo proceso hijo. | Detección de fallas. | Muerte de proceso hijo. | `Exit_Code_Log_Exists == True`. |
| **PRC-I22** | `INV_STACK_LIMIT` | El límite de pila (stack) de ejecución está configurado estáticamente a 8MB. | Previene recursiones infinitas. | Arranque de runtime. | `Stack_Limit == 8MB`. |
| **PRC-I23** | `INV_PID_LOCK` | Los ficheros lock contienen el PID validado del proceso que los mantiene. | Previene bloqueos huérfanos. | Escritura de lock. | `is_process_active(PID) == True`. |
| **PRC-I24** | `INV_NS_ISOLATION` | Los workers corren bajo aislamiento de namespaces de Unix. | Protección a nivel de kernel. | Configuración de runtime. | `Namespace_Isolated == True`. |
| **PRC-I25** | `INV_CONNS_CAP_WORK`| El número máximo de subprocesos workers concurrentes es de 50. | Evita saturación de CPU física. | Configuración de orquestador. | `Workers_Concurrent <= 50`. |
| **PRC-I26** | `INV_IPC_PAYLOAD_MAX`| El tamaño máximo permitido para payloads de mensajes IPC es de 2MB. | Evita colapso de buffer local. | Lectura de socket Unix. | `Payload_Size <= 2MB`. |
| **PRC-I27** | `INV_TENANT_TMP` | Las rutas temporales de trabajo se segregan por tenant_id. | Garantía de aislamiento. | Creación de workspace. | `contains(tenant_id) == True`. |
| **PRC-I28** | `INV_NX_DATA_PAGES` | Las páginas de datos de memoria se configuran con flags no-execute (NX). | Previene exploits de shellcode. | Carga de binario. | `NX_Enabled == True`. |
| **PRC-I29** | `INV_PROXY_ONLINE` | El proxy de inferencia local debe estar en línea antes del spawn. | Evita ejecuciones huérfanas. | Pre-spawn check. | `Proxy_Responding == True`. |
| **PRC-I30** | `INV_LOAD_DEGRADE` | Si la carga de CPU supera el 90%, el enjambre degrada a Flash T=0.0. | Conservación de energía. | Monitor de carga. | `CPU_Usage > 90% -> Downgrade`. |

## MATRIZ 3: 5 ANTIPATRONES ESTOCÁSTICOS (PRC-AP01..05)
Disfunciones lógicas y operativas en la contención de procesos y recursos.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **PRC-AP01** | **Bare Subprocess** | Lanzar subprocesos sin especificar límites de timeout en el supervisor. | `subprocess.run` sin parámetro `timeout`. | Workers colgados congelan el supervisor. | Usar `asyncio.wait_for` con timeout de 15s. |
| **PRC-AP02** | **Connection Crossover**| Compartir el mismo descriptor de conexión SQL entre el padre y el proceso hijo fork. | `sqlite3.ProgrammingError` en llamadas post-fork. | Corrupción de la integridad física de SQLite. | Cerrar conexiones en el hijo y abrirlas post-fork. |
| **PRC-AP03** | **Busy Queue Polling** | Leer colas de mensajería IPC mediante bucles sleep activos (active polling). | `while True: sleep(0.5)` en lectura. | Consumo inútil de CPU (anergía de CPU). | Usar lecturas asíncronas bloqueantes por sockets. |
| **PRC-AP04** | **Silent Return Codes** | Ignorar los códigos de salida de los subprocesses asumiendo que todo fue exitoso. | `returncode` no verificado en `execute()`. | Fallas de ejecución ocultadas en base de datos. | Aserción estricta de `returncode == 0`. |
| **PRC-AP05** | **Shared User Execution**| Ejecutar workers y supervisor bajo el mismo UID de root del sistema. | `os.getuid() == 0` en subagentes. | Escalado de privilegios y brecha total del host. | Configurar usuario sin privilegios en el fork. |

## MATRIZ 4: 4 REDUNDANCIAS ACTIVAS (PRC-RA01..04)
Estructuras redundantes para continuidad operativa y control de procesos.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **PRC-RA01** | **Dual Supervisors** | Supervisor principal + Daemon watchdog en proceso segregado. | Falla catastrófica del event loop principal. | CPU Cycle imperceptible. | `cortex/worker/` |
| **PRC-RA02** | **Unix + Memory IPC** | Bus local AF_UNIX + canal de memoria compartida de respaldo. | Pérdida de mensajes en socket local Unix congestionado. | Duplicación mínima de memoria. | `multiprocessing.Queue` |
| **PRC-RA03** | **Backup Worker Pool** | Pool de workers inactivos listos para swap inmediato. | Caída brusca de nodos por OOM en cgroups. | Carga de memoria en reposo. | `LegionPool` |
| **PRC-RA04** | **Replicated State Map**| Copia de estado en RAM local sincronizada con DB SQLite WAL. | Corrupción del archivo sqlite por caída física. | Sincronización I/O adicional. | `CausalStateStore` |

## MATRIZ 5: 8 VECTORES DE ATAQUE ADVERSARIAL (PRC-AV01..08)
Técnicas de inyección de caos y penetración en el sandbox de procesos.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **PRC-AV01** | **Shared Library Hijack**| LD_LIBRARY_PATH local. | Inyección de librería nativa `.so` maliciosa para alterar ONNX. | Ejecución de código arbitrario en host. | safe_env estricto y pathing absoluto. |
| **PRC-AV02** | **Resource Starvation** | Event Bus IPC. | Inundar de llamadas síncronas pesadas para colapsar la CPU del host. | Denegación de servicio de agentes (OOM). | Cgroups límites estrictos (INV_CGROUP_LIMIT). |
| **PRC-AV03** | **Signal Flooding** | Tabla de señales del SO. | Enviar ráfagas de señales SIGINT al PID del supervisor. | Apoptosis accidental del sistema completo. | Captura selectiva y bloqueo de señales. |
| **PRC-AV04** | **Host Env Bleed** | API de variables de entorno. | Manipulación de entorno para filtrar tokens de API. | Exfiltración de claves de producción. | safe_env stripping en runtime. |
| **PRC-AV05** | **IPC Injection** | AF_UNIX local socket. | Escribir mensajes maliciosos directamente en el socket Unix local. | Alteración del flujo de ejecución del enjambre. | Permisos estrictos de lectura/escritura a socket. |
| **PRC-AV06** | **Zombie Leak DOS** | Tabla de procesos de kernel. | Spawn masivo de workers sin llamar a waitpid. | Agotamiento de PID de kernel (fork bomb). | Reap automático periódico (waitpid). |
| **PRC-AV07** | **Temp Workspace Clash**| Directorio `/tmp/cortex_swarm`. | Creación manual de enlaces simbólicos para secuestrar rutas. | Sobreescritura de archivos del host. | UUID en paths y segregación (INV_UUID_WORKSPACE).|
| **PRC-AV08** | **Fork Bomb Attack** | Payload Python inyectado. | payload.py inicia spawns recurrentes de sí mismo sin control. | Saturación y caída por kernel panic del host. | Límites estrictos ulimit y cgroups CPU. |
