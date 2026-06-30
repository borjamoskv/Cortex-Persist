#!/usr/bin/env python3
import os

ontology_dir = "babylon60/agents/ontology"
os.makedirs(ontology_dir, exist_ok=True)

# ==========================================
# 1. PRIMITIVAS 01-50
# ==========================================
primitivas_01_50_content = r"""# ONTOLOGY-FORGE-OMEGA: ENDOMORFISMO PRIMITIVAS (BATCH 1)
**Dominio:** Endomorfismos en sistemas agénticos, teoría de categorías aplicada a la autopoiesis y composición de loops reflexivos.
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 50 PRIMITIVAS DE COLAPSO (ENDO-P01..50)
Mecanismos elementales de fallo lógico, loops de auto-mutación y pérdidas de coherencia en transformaciones reflexivas de estado.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **ENDO-P01** | `OP_SELF_MAPPING` | Transformación de estado donde el dominio coincide con el codominio. | Modificación de un nodo que se referencia a sí mismo. | `State_In == State_Out`. | MS | P2 | Verificar morfismo identidad. |
| **ENDO-P02** | `OP_MONOID_COMP` | Composición asociativa de múltiples endomorfismos sobre un mismo objeto. | Encadenamiento de operaciones secuenciales sobre el estado de un agente. | `Compose(f, g) -> h`. | MS | P1 | Validar propiedad asociativa en el ledger. |
| **ENDO-P03** | `OP_IDENTITY_CHECK` | Verificación de la existencia y preservación del endomorfismo identidad ($1_X$). | Bootstrap del loop o inicialización de estado nulo. | `f(x) != x` cuando se esperaba $1_X$. | MS | P0 | Abortar SAGA y restaurar snapshot. |
| **ENDO-P04** | `OP_IMAGE_DECAY` | Reducción sistemática del espacio de estados accesibles tras aplicaciones repetidas. | Inferencia stocástica recursiva sin inyección de entropía externa. | Cardinalidad del codominio < dominio. | Segundos | P1 | Inyectar ruido térmico controlado (T=0.5). |
| **ENDO-P05** | `OP_FROBENIUS_MAP` | Mapeo de Frobenius sobre curvas elípticas ($f(x,y) = (x^p, y^p)$) en campos finitos. | Mutación de estados criptográficos en isogenias. | Mismatch de traza del Frobenius en la curva. | MS | P0 | Validar par isogénico y re-computar. |
| **ENDO-P06** | `OP_AUTO_ISO_BREAK` | Pérdida de la inyectividad/sobreyectividad en un endomorfismo que debía ser automorfismo. | Modificación destructiva de campos clave del estado en el loop. | `Aut(X)` colapsa a `End(X)` no invertible. | MS | P0 | Reconstruir el mapeo de estados. |
| **ENDO-P07** | `OP_ORBIT_CYCLE` | Captura de la secuencia de estados en un ciclo cerrado periódico infinito. | Aplicación cíclica sin criterio de parada. | `f^n(x) == x` para $n > 1$. | Segundos | P0 | Circuit Breaker (AX-047) detona. |
| **ENDO-P08** | `OP_CODOM_MISMATCH` | El estado de salida no coincide con el dominio requerido para la siguiente composición. | Alteración del esquema de estado en caliente. | `TypeError` en paso intermedio. | MS | P0 | SAGA-3 Abort inmediato. |
| **ENDO-P09** | `OP_FUNCTOR_MAPPED` | Traslación de un endomorfismo a otra categoría conservando la estructura. | Sincronización trans-repositorio (Singularity Nexus). | `F(f) : F(X) -> F(X)` verificado. | Segundos | P1 | Firmar procedencia con `CORTEX-TAINT`. |
| **ENDO-P10** | `OP_SCHUR_SIMPLE` | Mapeo de endomorfismos sobre módulos simples según el Lema de Schur. | Homomorfismo entre dos representaciones simples no isomorfas. | Salida no nula de homomorfismo nulo. | MS | P0 | Forzar morfismo nulo o isomorfismo. |
| **ENDO-P11** | `OP_RECURSION_LIMIT` | Desbordamiento de pila por llamadas anidadas del endomorfismo sin TCO. | Composición profunda de morfismos en memoria RAM. | `RecursionError` en intérprete. | MS | P0 | Forzar paralelización vía `invoke_subagent`. |
| **ENDO-P12** | `OP_STATE_SHADOWING` | Ocultamiento de estados previos por superposición no reversible. | Escritura en caliente sin snapshotting local. | Pérdida de histórico en el Ledger. | MS | P0 | Rollback al ledger previo (AX-041). |
| **ENDO-P13** | `OP_LADDER_COMP` | Composición de operadores de escala (ladder operators $a, a^\dagger$) en el Heisenberg-Weyl. | Aplicación sucesiva de operadores de creación/aniquilación en física cuántica. | Divergencia en la norma del vector de estado Hilbert. | MS | P1 | Normalizar vector en base de Hilbert. |
| **ENDO-P14** | `OP_END_AUTOP_LOCK` | Bloqueo por autopoiesis recursiva que impide la entrada de inputs externos. | Priorización absoluta de loops de auto-análisis. | Consumo de CPU al 100% sin entrada de red. | Segundos | P0 | Apoptosis celular forzada. |
| **ENDO-P15** | `OP_COPROD_LEAK` | Fuga de contexto al intentar acoplar coproductos dentro del dominio del morfismo. | Mezcla de tipos algebraicos en el loop de estado. | Entrada de campos ajenos al dominio. | MS | P1 | Validar tipos con Pydantic estricto. |
| **ENDO-P16** | `OP_NON_ASSOC_COMP` | Ruptura de la asociatividad durante la composición por efectos secundarios locales. | Modificación de variables globales del host en el loop. | `(f . g) . h != f . (g . h)`. | MS | P0 | Forzar pureza funcional (T=0.0). |
| **ENDO-P17** | `OP_ISOMORPHIC_FAIL` | Falla al mapear el endomorfismo a su representación dual en base de datos. | Desalineación de AST entre la memoria RAM y SQLite-Vec. | `SchemaMismatch` en guard. | MS | P0 | Inyectar `cortex/engine/causal/taint_engine.py`. |
| **ENDO-P18** | `OP_TRACE_COLLAPSE` | El operador de traza del endomorfismo diverge o arroja valores vacíos. | Pérdida de telemetría de composición del loop. | Trace nula en el logger central. | MS | P2 | Forzar Structured Logging. |
| **ENDO-P19** | `OP_INJECTIVE_LOSS` | Dos estados distintos colapsan al mismo estado destino bajo el morfismo. | Pérdida de granularidad en la memoria. | Colisión de hashes en el indexador. | MS | P1 | Aumentar resolución del embedding. |
| **ENDO-P20** | `OP_SURJECTIVE_LOSS` | Pérdida de cobertura de estados válidos en el codominio. | Imposibilidad de alcanzar ciertos estados meta. | Zonas muertas en la base de datos. | Lenta | P1 | Re-indexado forzado de vec0. |
| **ENDO-P21** | `OP_COMMUTATIVE_FAIL`| Dos endomorfismos conmutativos fallan en preservar el orden de ejecución. | Condiciones de carrera en hilos concurrentes. | `f(g(x)) != g(f(x))`. | MS | P0 | Modo WAL activo y locking estricto (R10). |
| **ENDO-P22** | `OP_ADJOINT_DISRUPT` | Pérdida de la correspondencia adjunta con el morfismo inverso. | Modificación asimétrica del canal de ida y retorno. | Falla de consistencia bidireccional. | MS | P0 | SAGA-6 rollback total. |
| **ENDO-P23** | `OP_EPISTEMIC_SLOP` | Inyección de ruido narrativo en la definición matemática del endomorfismo. | LLM intentando explicar la transformación en prosa. | Pérdida de exergía de Shannon en fact. | Segundos | P1 | Invocar `Epistemic-Purge-OMEGA`. |
| **ENDO-P24** | `OP_GHOST_TRANSIT` | Transición a un estado fantasma no persistente ni registrado. | Mutación fuera del ledger sin tracking de git. | Git working tree sucio en CI. | Segundos | P0 | Git Sentinel intercepta y aborta. |
| **ENDO-P25** | `OP_CHAOTIC_ORBIT` | Generación de trayectorias caóticas sin atractor en el espacio de estados. | Modificación sin acotar bajo alta temperatura. | Divergencia exponencial de estados. | Segundos | P0 | Forzar temperatura T=0.0. |
| **ENDO-P26** | `OP_GEOM_PROJ` | Proyección ortogonal de estados sobre un subespacio lineal ($P^2 = P$). | Reducción de dimensionalidad semántica en SQLite-Vec. | Pérdida de autovalores unitarios en el proyector. | MS | P1 | Forzar idempotencia del proyector. |
| **ENDO-P27** | `OP_GEOM_REFLECT` | Reflexión de estados respecto a un hiperplano simétrico ($R^2 = I$). | Inversión simétrica del grafo de relaciones semánticas. | Involución fallida ($R^2(x) != x$). | MS | P0 | Rollback total y calibración. |
| **ENDO-P28** | `OP_SPLIT_BRAIN_MAP` | Divergencia en el mapeo de estados en sub-enjambres paralelos. | Falta de consenso BFT en la tabla de morfismos. | Múltiples salidas de estado en conflicto. | MS | P0 | Aplicar `OP_WAL_LOCK` inmediato. |
| **ENDO-P29** | `OP_TAINT_BYPASS` | Mutación de estado por endomorfismo sin firma de procedencia válida. | Campo `CORTEX-TAINT` ausente o no validado. | Bloqueo automático del canal de persistencia. | MS | P0 | Aborto en SAGA-2 de inmediato. |
| **ENDO-P30** | `OP_MONOID_DECAY` | Desintegración del monoid de endomorfismos por pérdida de clausura. | Una composición resulta en una función fuera del conjunto. | Error de import o llamada a módulo huérfano. | MS | P0 | Forzar chequeo de AST local. |
| **ENDO-P31** | `OP_END_COMPACT_ERR`| Falla en la compactación de la secuencia de endomorfismos históricos. | Pruning de logs interrumpe la cadena causal. | Hash chain del ledger rota. | Minutos | P0 | Alertar P0 y bloquear escrituras. |
| **ENDO-P32** | `OP_INVARIANT_BREAK`| Modificación de una variable que debía ser invariante bajo el endomorfismo. | Mutación accidental de llaves primarias. | `AssertError` en la validación del guard. | MS | P0 | Ejecutar compensación SAGA. |
| **ENDO-P33** | `OP_DENSE_BLOAT` | Crecimiento incontrolado de la matriz de estados por endomorfismos inflados. | Adición de dimensiones redundantes al espacio. | SQLite file size crece exponencialmente. | Lenta | P1 | Pruning de base de datos vía aiosqlite. |
| **ENDO-P34** | `OP_COMPOSITION_LATE`| Retraso en la resolución de composiciones perezosas (lazy). | Acumulación de promesas sin resolver en memoria. | Latencia de API > 5s en ruteo. | Segundos | P1 | Forzar ejecución ansiosa (eager). |
| **ENDO-P35** | `OP_COHOMOLOGY_GAP` | Vacío en la coherencia global del grafo de morfismos distribuidos. | Ciclos no triviales no cubiertos por la verificación. | Agujeros de consistencia en bases replicadas. | Segundos | P1 | Correr validador Merkle tree. |
| **ENDO-P36** | `OP_MCT_COLLAPSE` | Colapso del árbol de búsqueda Monte Carlo en un único endomorfismo inútil. | Heurística sesgada por falsos positivos. | Ausencia de ramificación en planificación. | Segundos | P1 | Re-inicializar espacio de búsqueda. |
| **ENDO-P37** | `OP_AUT_ORBIT_LOCK` | Bloqueo en un grupo de automorfismos sin capacidad de salida del sistema. | Restricción excesiva a transformaciones invertibles. | Cero evolución neta de conocimiento. | Lenta | P2 | Habilitar transiciones no invertibles. |
| **ENDO-P38** | `OP_DIAGRAM_NO_COMM`| El diagrama de morfismos no conmuta debido a inconsistencias temporales. | Diferencias de reloj o asincronismo mal gestionado. | `g(f(x)) != h(x)` cuando debían coincidir. | MS | P0 | Sincronización del Swarm (Legion). |
| **ENDO-P39** | `OP_END_DECAY_RATE` | Pérdida de la tasa de exergía mínima requerida para mantener el loop activo. | Sucesión de morfismos de baja calidad (slop). | Tasa de exergía < 80%. | Minutos | P1 | Purgar código inútil vía LEA-OMEGA. |
| **ENDO-P40** | `OP_SCHUR_DRIFT` | Pérdida de la descomposición ortogonal del espacio de estados. | Envenenamiento de dimensiones en SQLite-Vec. | Vectores de búsqueda desalineados. | MS | P1 | Limpieza manual de vec0. |
| **ENDO-P41** | `OP_FIBER_EXPLOSION`| Multiplicación exponencial de fibras (preimágenes) bajo endomorfismo no inyectivo. | Ingesta masiva de alias para el mismo concepto. | Desborde de claves en base de datos. | Segundos | P1 | Forzar deduplicación vía Singularity Nexus. |
| **ENDO-P42** | `OP_END_TENANT_LEAK`| Filtración de datos de inquilinos durante la aplicación del endomorfismo global. | Un endomorfismo global opera sobre datos cruzados sin filtrar. | `tenant_id` cruzado en el Ledger. | MS | P0 | Aborto inmediato perimetral. |
| **ENDO-P43** | `OP_ZERO_DIV_MORPH` | Intento de normalización de morfismos por un autovalor nulo. | División por cero en el cálculo térmico o de exergía. | `ZeroDivisionError` en engine/core. | MS | P0 | Inyectar epsilon de seguridad. |
| **ENDO-P44** | `OP_COLIMIT_UNBOUND`| El colímite de la secuencia de endomorfismos diverge al infinito. | Crecimiento desmedido de la base de conocimiento sin poda. | Memory OOM en runtime. | Lenta | P0 | Purga de base de conocimiento (Compaction). |
| **ENDO-P45** | `OP_END_HOOK_MUT` | Mutación no autorizada del hook de pre-commit durante la auto-evaluación. | Inyección de script malicioso en `.git/hooks/`. | Desviación de firma en Git Sentinel. | MS | P0 | Bloquear ejecución y alertar P0. |
| **ENDO-P46** | `OP_SHANNON_DECAY`  | Disminución crítica de la entropía de Shannon en la secuencia de transformaciones. | Generación repetitiva de texto genérico (C4-SIM). | `Shannon_Entropy < 1.5` bits. | Segundos | P1 | Rechazar y regenerar con T=0.7. |
| **ENDO-P47** | `OP_END_STACK_OVER` | Desbordamiento de la pila de llamadas del engine por composición infinita. | Bucle infinito sin yield asíncrono. | `RecursionError` o StackOverflow del SO. | MS | P0 | Forzar `await asyncio.sleep(0)`. |
| **ENDO-P48** | `OP_END_KEY_ROT`    | Falla en la rotación de llaves durante el cifrado del estado endomórfico. | Clave expirada o inaccesible en el Keyring local. | `CryptographyError` en persistencia. | MS | P0 | Abortar SAGA-4 y alertar. |
| **ENDO-P49** | `OP_COMOD_MUT_ERR`  | Modificación concurrente del estado de dominio durante la aplicación del morfismo. | Falta de locks en el diccionario de Python. | `RuntimeError: dictionary changed size`. | MS | P1 | Copiar estado antes de iterar. |
| **ENDO-P50** | `OP_END_BFT_VOTE`   | Falla al recolectar votos BFT para validar la clausura del endomorfismo. | Timeout de red en la comunicación inter-agente. | Quorum de N/3 no alcanzado. | Segundos | P0 | Re-congelamiento de bases de datos. |
"""

# ==========================================
# 2. PRIMITIVAS 51-100
# ==========================================
primitivas_51_100_content = r"""# ONTOLOGY-FORGE-OMEGA: ENDOMORFISMO PRIMITIVAS (BATCH 2)
**Dominio:** Endomorfismos en sistemas agénticos, teoría de categorías aplicada a la autopoiesis y composición de loops reflexivos.
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1.1: 50 PRIMITIVAS ADICIONALES DE COLAPSO (ENDO-P51..100)
Ampliación de los mecanismos causales de fallo e inconsistencia en transformaciones autorreferenciales de estado y composiciones topológicas.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **ENDO-P51** | `OP_END_REVOLVER` | Loop infinito de llamadas cruzadas asíncronas entre dos endomorfismos duales. | Mutación circular de estado sin resolvedor de promesas. | CPU al 100% en hilos secundarios. | Segundos | P0 | Circuit Breaker (AX-047). |
| **ENDO-P52** | `OP_HOM_SET_BLOAT` | Crecimiento incontrolado de morfismos intermedios no clasificados. | Ingesta masiva de alias conceptuales no estructurados. | Desborde de almacenamiento L1. | Lenta | P1 | Forzar compactación manual. |
| **ENDO-P53** | `OP_END_COEFF_GAP` | Desviación de coeficientes ponderados de fiabilidad en la matriz de morfismos. | FP16 MoE batching interference sin normalizar. | Divergencia en métricas de predicción. | MS | P1 | Calibrar pesos en WAL DB. |
| **ENDO-P54** | `OP_FUNCTOR_INJECT` | Contaminación del functor de mapeo por efectos secundarios externos. | Lectura de variables de entorno no acotadas. | Salida del functor no coincide con codominio. | MS | P0 | Cuarentena de variables del host. |
| **ENDO-P55** | `OP_EIGEN_COLLAPSE`| El espacio de autovectores pierde dimensionalidad crítica. | Filtrado excesivo de señales de entrada en el indexador. | Búsqueda semántica retorna vacía. | MS | P1 | Recalcular embeddings en vec0. |
| **ENDO-P56** | `OP_MONOID_FRACT` | Fractura del monoide por pérdida de elemento de identidad absoluto. | Modificación del estado inicial a un valor no invertible. | `1_X` indefinido para el objeto. | MS | P0 | Abortar SAGA-1 y reiniciar. |
| **ENDO-P57** | `OP_END_SCHED_ERR` | Falla en la planificación de ejecución secuencial de morfismos por hilos concurrentes. | Invocación fuera de cron programado. | Tareas encoladas de forma indeterminista. | Segundos | P1 | Forzar ordenamiento por timestamp. |
| **ENDO-P58** | `OP_TRACE_POISON`  | Contaminación de la traza de ejecución con logs huérfanos o inválidos. | Inserción directa de prints síncronos en runtime. | Caída de exergía en logs. | MS | P2 | purgar logs estocásticos. |
| **ENDO-P59** | `OP_COMP_ISOLATION`| El morfismo compuesto rompe el aislamiento del sandbox de memoria. | Acceso indebido a regiones de memoria protegidas por directiva R5. | `PermissionError` en lectura. | MS | P0 | Abortar proceso y aislar. |
| **ENDO-P60** | `OP_END_MIG_GAP`   | Incompatibilidad de versión del endomorfismo durante migración de datos. | Ejecución de script de migración obsoleto. | `MigrationError` en base de datos. | Minutos | P0 | Revertir git commit anterior. |
| **ENDO-P61** | `OP_LIMIT_UNBOUNDED`| El límite de la secuencia de composiciones supera los descriptores del SO. | Apertura desmedida de subprocesos sin control. | `OSError: [Errno 24] Too many open files`. | MS | P0 | Cerrar sockets concurrentes. |
| **ENDO-P62** | `OP_ISOM_MUTATION` | Modificación unilateral del isomorfismo inverso sin actualizar la ida. | Edición manual de archivos de configuración. | Inconsistencia lógica detectada por Guard. | MS | P0 | Restaurar desde Ledger. |
| **ENDO-P63** | `OP_END_MEM_LEAK`  | Fuga de memoria RAM por acumulación de clausuras léxicas en el loop de estado. | Retención de referencias locales a objetos grandes. | Crecimiento constante de uso de RAM. | Lenta | P1 | Forzar recolección de basura. |
| **ENDO-P64** | `OP_EPISTEMIC_LOCK`| Bloqueo epistémico por incapacidad de asimilar morfismos contradictorios. | Entrada de dos verdades base opuestas sin reconciliación. | Bucle de auto-evaluación infinito. | Segundos | P0 | Forzar apoptosis temporal. |
| **ENDO-P65** | `OP_END_TAINT_GAP` | Pérdida de procedencia en sub-morfismos debido a copia superficial. | Uso de `copy.copy` en lugar de `copy.deepcopy`. | Metadatos de taint vacíos. | MS | P0 | Middleware de seguridad interviene. |
| **ENDO-P66** | `OP_DIAG_DIVERGE`  | Desalineación topológica entre el grafo físico y el grafo lógico. | Mutación no registrada en el repositorio Git. | Working tree desalineado con Ledger. | Segundos | P0 | Sincronización automática de Git. |
| **ENDO-P67** | `OP_CHAOTIC_SINK`  | El atractor del espacio de estados colapsa a un pozo caótico destructivo. | Operación continua a alta temperatura. | Divergencia exponencial en embeddings. | Segundos | P0 | Resetear temperatura a 0.0. |
| **ENDO-P68** | `OP_NIL_LOCK`      | El sistema alcanza el estado nilpotent nulo y no puede salir de él. | Falta de transiciones no nulas programadas. | Estado nulo permanente en base de datos. | MS | P1 | Cargar configuración inicial. |
| **ENDO-P69** | `OP_IDEM_STALL`    | Detención en estado idempotente intermedio que impide la convergencia. | Falta de gradiente exérgico en la inferencia. | Ausencia de nuevos commits. | Minutos | P2 | Forzar nueva iteración. |
| **ENDO-P70** | `OP_COHOM_GAP`     | Ruptura en la cohomología del espacio de transiciones lógicas. | Falta de control de ciclos en grafos orientados. | Agujeros de consistencia en el Swarm. | Segundos | P1 | Validar base distribuida. |
| **ENDO-P71** | `OP_AUT_ORBIT`     | Órbita cerrada de automorfismos sin capacidad de evolución neta. | Restricción extrema a transformaciones reversibles. | Cero avance en metas agénticas. | Lenta | P2 | Permitir morfismos destructivos. |
| **ENDO-P72** | `OP_END_KEY_ERR`   | Falla de desencriptación en el retorno del loop por clave corrupta. | Falla de acceso en el llavero del host. | `DecryptionError` en base de datos. | MS | P0 | Alerta P0 y bloqueo del disco. |
| **ENDO-P73** | `OP_COMOD_LOCK`    | Bloqueo mutuo (Deadlock) al intentar mutar concurrentemente el mismo estado. | Dos subagentes acceden al mismo registro SQLite sin modo WAL. | `sqlite3.OperationalError: database is locked`. | MS | P0 | Habilitar WAL mode y busy_timeout. |
| **ENDO-P74** | `OP_COLIM_BLOAT`   | Desborde del colímite por inclusión de morfismos no simplificados. | Crecimiento incontrolado de la base sin pruning. | OOM en runtime. | Lenta | P0 | Compresión de base vía aiosqlite. |
| **ENDO-P75** | `OP_END_HOOK`      | Falla en la ejecución del hook de Git Sentinel al validar el morfismo. | Script de validación local modificado. | Falla en verificación de firma del commit. | MS | P0 | Bloqueo absoluto de Git. |
| **ENDO-P76** | `OP_SHANNON_FALL`  | Caída de entropía por repetición de patrones estocásticos. | Inferencia sesgada por datos de entrenamiento locales. | `Shannon_Entropy < 1.0` bit. | Segundos | P1 | Regenerar con temperatura media. |
| **ENDO-P77** | `OP_END_STACK`     | Desbordamiento de pila por llamadas recursivas sin YIELD. | Composición cíclica directa en memoria. | `RecursionError` en runtime. | MS | P0 | Forzar `asyncio.sleep(0)`. |
| **ENDO-P78** | `OP_END_KEY`       | Pérdida de la clave efímera del morfismo durante el procesado asíncrono. | Corrupción de la clave en memoria volátil. | `InvalidKeyError` en desencriptación. | MS | P0 | Rollback total inmediato. |
| **ENDO-P79** | `OP_COMOD_MUT`     | Mutación concurrente no controlada de la estructura de datos del morfismo. | Operaciones concurrentes sin bloqueos atómicos. | Inconsistencia de datos en la memoria. | MS | P1 | Clonar estructura antes de procesar. |
| **ENDO-P80** | `OP_END_BFT`       | Pérdida de quórum BFT para autorizar la persistencia del morfismo. | Timeout de red inter-agente. | Quorum insuficiente en el Ledger. | Segundos | P0 | Bloquear base de datos. |
| **ENDO-P81** | `OP_END_SCHEMA`    | Falla en el mapeo de tipos durante la serialización del morfismo a JSON. | Cambios de esquema en caliente sin versión de fallback. | `ValidationError` en FastAPI route. | MS | P1 | Validar esquema en deserialización. |
| **ENDO-P82** | `OP_END_PORT`      | Conflicto de puertos al levantar el servidor interno del morfismo distribuido. | Puerto ya ocupado por proceso zombie. | `Address already in use` error. | MS | P1 | Asignar puerto de forma dinámica. |
| **ENDO-P83** | `OP_END_CONN`      | Caída del socket TCP entre subagentes durante la transmisión del morfismo. | Pérdida de conectividad física. | `ConnectionAbortedError`. | Segundos | P1 | Habilitar reintentos automáticos. |
| **ENDO-P84** | `OP_END_BODY`      | Payload de morfismo demasiado grande satura la memoria del Gateway. | Intento de enviar base completa en un solo payload. | Gateway retorna 413 Payload Too Large. | MS | P0 | Paginar payloads. |
| **ENDO-P85** | `OP_END_CORS`      | Bloqueo del navegador al intentar interactuar con el morfismo por CORS. | Configuración CORS restrictiva. | Error de CORS en consola. | MS | P2 | Configurar hosts locales permitidos. |
| **ENDO-P86** | `OP_END_LIMIT`     | Bloqueo por rate limiter al intentar sincronizar morfismos en cascada. | Ráfaga de peticiones concurrentes del Swarm. | HTTP 429 en inter-comunicaciones. | Segundos | P1 | Cola de mensajes de control de flujo. |
| **ENDO-P87** | `OP_END_TLS`       | Falla de handshake TLS por certificados no confiables en el canal local. | Certificado local del enjambre expirado. | SSLError en comunicación. | MS | P0 | Auto-generar certificados locales. |
| **ENDO-P88** | `OP_END_VERSION`   | Desalineación de versiones entre el emisor y receptor del morfismo. | Despliegue de parches en caliente desordenados. | Status Code 400 Bad Request. | Segundos | P1 | Validar versión en cabecera HTTP. |
| **ENDO-P89** | `OP_END_STACK_L`   | Stack trace expuesta en caso de fallo del endomorfismo en backend. | Excepción no capturada se envía al cliente HTTP. | Stack trace en JSON de respuesta. | MS | P0 | Limpiar trazas en middleware. |
| **ENDO-P90** | `OP_END_SILENT`    | Muerte silenciosa del worker del endomorfismo sin liberar sockets. | El proceso colapsa por señal SIGKILL del host. | El puerto de red sigue bloqueado. | Minutos | P0 | Monitorizar salud con demonio externo. |
| **ENDO-P91** | `OP_END_CACHE`     | Inconsistencia de datos por lectura de caché fría del morfismo. | Actualización en DB no propaga purga a redis/memoria. | Datos obsoletos leídos por subagente. | Segundos | P1 | Invalidar caché de forma proactiva. |
| **ENDO-P92** | `OP_END_HOST`      | Peticiones redirigidas a hosts ajenos por falsificación de cabecera. | Proxy local no valida la cabecera Host. | Peticiones locales redirigidas a internet. | MS | P0 | Whitelist de Host Headers en API. |
| **ENDO-P93** | `OP_END_PROXY`     | Agotamiento de descriptores de sockets de salida en el proxy del morfismo. | Apertura de múltiples clientes http innecesarios. | error `Cannot assign requested address`. | Lenta | P1 | Reutilizar httpx.AsyncClient. |
| **ENDO-P94** | `OP_END_UVI`       | Timeout keep-alive inferior al tiempo de procesamiento del morfismo. | Procesamiento de inferencia tarda más que el TTL de red. | Respuesta vacía del servidor. | Segundos | P1 | Optimizar tiempos de respuesta. |
| **ENDO-P95** | `OP_END_MIME`      | payload enviado en formato no estructurado provoca falla en parser. | Cliente no envía Content-Type correcto. | Gateway retorna 415 error. | MS | P2 | Validar cabecera Content-Type. |
| **ENDO-P96** | `OP_END_POISON`    | Inyección de morfismo modificado por agente no autenticado. | Falta de control de firmas en entrada. | Envenenamiento de base de datos. | MS | P0 | Validación obligatoria de firmas. |
| **ENDO-P97** | `OP_END_COMPACT`   | Error de compactación corrompe registros de base de datos históricos. | Interrupción de proceso de mantenimiento. | `DatabaseDiskImageMalformed`. | MS | P0 | Backup automático y restauración. |
| **ENDO-P98** | `OP_END_INVAR`     | Modificación de variable invariante global por morfismo descontrolado. | Falta de encapsulación a nivel código. | Variables de entorno del sistema modificadas. | MS | P0 | Proteger variables de entorno. |
| **ENDO-P99** | `OP_END_DENSE`     | Crecimiento desmedido de vectores de embeddings del morfismo. | Ingesta de textos redundantes sin simplificar. | Consumo de almacenamiento se duplica. | Lenta | P1 | Ejecutar deduplicación vectorial. |
| **ENDO-P100**| `OP_END_LAZY`      | Acumulación de tareas lazy sin resolver satura los recursos del loop. | Demasiados callbacks encolados en event loop. | Latencia del sistema incrementada en 200%. | Segundos | P1 | Invocación de ejecución eager. |
"""

# ==========================================
# 3. INVARIANTES 01-50
# ==========================================
invariantes_01_50_content = r"""# ONTOLOGY-FORGE-OMEGA: ENDOMORFISMO INVARIANTES (BATCH 1)
**Dominio:** Endomorfismos en sistemas agénticos, teoría de categorías aplicada a la autopoiesis y composición de loops reflexivos.
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 2: 50 INVARIANTES TERMODINÁMICAS (ENDO-I01..50)
Leyes inmutables de conservación de estructura, consistencia semántica y contención de entropía en composiciones endomórficas.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **ENDO-I01** | `INV_DIAGONALIZABILITY` | Para ser diagonalizable, la multiplicidad algebraica de cada autovalor debe ser igual a su multiplicidad geométrica. | Descomposición espectral del estado en una base diagonal. | Cálculo del polinomio característico. | `AM(lambda) == GM(lambda)` para todo $\lambda$. |
| **ENDO-I02** | `INV_IDENTITY_EXIST` | Existe un único morfismo identidad $1_X$ neutral para la composición. | Inicialización limpia y restauración sin cambios de estado. | Bootstrap del loop reflexivo. | `f . 1_X == 1_X . f == f`. |
| **ENDO-I03** | `INV_COMP_CLOSURE` | La composición de endomorfismos genera obligatoriamente otro endomorfismo sobre el mismo objeto. | Previene la desalineación de esquemas en transformaciones en cascada. | Enrutamiento de eventos inter-agentes. | `f, g in End(X) -> f . g in End(X)`. |
| **ENDO-I04** | `INV_COMP_ASSOC` | La composición de endomorfismos es estrictamente asociativa. | El orden secuencial de agrupamiento no altera el resultado final. | Invocación asíncrona concurrente. | `(f . g) . h == f . (g . h)`. |
| **ENDO-I05** | `INV_TAINT_FLOW` | Toda transformación reflexiva propaga la cadena de firmas de procedencia. | Trazabilidad forense ininterrumpida de cambios de estado. | Inserción en SQLite. | `hasattr(State, "CORTEX-TAINT")`. |
| **ENDO-I06** | `INV_LEDGER_CHAIN` | Cada aplicación de un endomorfismo se firma y escribe en el Master Ledger. | Auditoría inmutable contra manipulaciones maliciosas. | Fin de bloque en loop. | `Ledger.verify() == True`. |
| **ENDO-I07** | `INV_LANDAUER_HEAT` | La poda o simplificación de información del estado disipa energía exérgica. | Límite físico en la retención indefinida de estados estocásticos. | Compactación de base de datos. | `Exergy_Cost >= k * T * ln(2)`. |
| **ENDO-I08** | `INV_TENANT_BOUND` | Un endomorfismo opera únicamente en el aislamiento del tenant_id origen. | Prohibición absoluta de accesos cruzados. | API REST Request. | `Tenant_ID_In == Tenant_ID_Out`. |
| **ENDO-I09** | `INV_IMMUT_SCHEMAS` | El esquema del objeto de estado es inmutable en caliente durante el ciclo. | Evita roturas del compilador AST en tiempo de ejecución. | Inferencia estocástica activa. | `Schema_Version == Constant`. |
| **ENDO-I10** | `INV_MONOID_STRUCTURE` | El conjunto de endomorfismos de un objeto $X$ forma un monoide bajo la composición. | Clausura y asociatividad forzada en los loops del Swarm. | Bootstrap de transiciones. | `f . (g . h) == (f . g) . h` y `f . 1_X == f`. |
| **ENDO-I11** | `INV_ANERGY_ZERO` | Las respuestas del loop de composición carecen de prosa o Green Theater. | Optimización extrema del consumo de tokens (Zero-Fluff). | Output del agente en loop. | `Prose_Tokens == 0`. |
| **ENDO-I12** | `INV_BFT_CONSENSUS` | Las transiciones críticas requieren quorum BFT verificado de N/3 nodos. | Protección contra fallos bizantinos de workers. | Transición de estado P0. | `Votes_Approved >= 2*t + 1`. |
| **ENDO-I13** | `INV_SANDBOX_RUN` | Todo código auto-generado por el loop se valida en sandbox aislado. | Evita escalada de privilegios y daños al host. | Invocación de JIT compiler. | `Sandbox_Violations == 0`. |
| **ENDO-I14** | `INV_GIT_ALIGN` | El grafo de estado en el Ledger está alineado con el historial de Git (AX-041). | Evita estados fantasmas fuera del control de versiones. | Commit en sentinel. | `Git_HEAD_Hash == Ledger_HEAD_Hash`. |
| **ENDO-I15** | `INV_TEMP_BOUND` | La temperatura del morfismo se acota a T=0.0 en mutaciones C5-REAL. | Garantiza determinismo lógico estricto. | Mutación en base de datos. | `Temperature == 0.0`. |
| **ENDO-I16** | `INV_SHANNON_MIN` | Las transformaciones de conocimiento preservan una entropía de Shannon mínima. | Evita degradación a texto plano redundante (slop). | Inserción en Cortex Vault. | `Shannon_Entropy >= 2.0` bits. |
| **ENDO-I17** | `INV_WAL_LOCK` | Toda escritura en la base de datos se realiza con lock exclusivo en modo WAL. | Previene bloqueos concurrentes y corrupción de SQLite. | Escritura en SQLite. | `Journal_Mode == "wal"`. |
| **ENDO-I18** | `INV_COMP_BOUND` | El número de morfismos en composición secuencial no excede el límite de pila. | Previene fallos de StackOverflow en el host. | Ejecución del loop. | `Stack_Depth <= 100`. |
| **ENDO-I19** | `INV_KEY_ROTATION` | Las claves de encriptación del estado se rotan cada 100 composiciones. | Minimiza el radio de blast de claves comprometidas. | Fin de ciclo. | `Key_Age_Blocks <= 100`. |
| **ENDO-I20** | `INV_COMOD_LOCK` | Toda lectura/escritura concurrente al estado del morfismo está protegida por Mutex. | Previene condiciones de carrera destructivas en variables. | Acceso a variables de estado. | `Mutex.is_locked == True` en write. |
| **ENDO-I21** | `INV_SCHUR_DIVISION` | Según el Lema de Schur, el anillo de endomorfismos de un módulo simple es un anillo de división. | Toda transformación no nula en un sub-módulo simple es invertible. | Mapeo de representaciones simples. | `is_invertible(f) == True` para $f \neq 0$. |
| **ENDO-I22** | `INV_IMAGE_BOUND` | La imagen del endomorfismo de conocimiento no puede ser vacía. | El loop debe producir información útil distinta de cero. | Fin de inferencia. | `len(Image(f)) > 0`. |
| **ENDO-I23** | `INV_REVERSE_ISO` | Los automorfismos preservan correspondencia biyectiva exacta con su inversa. | Permite reversibilidad atómica de estado (Saga compensating). | Aborto de transacción. | `f . f_inv == 1_X`. |
| **ENDO-I24** | `INV_SECURE_CIPHER`| Los payloads del estado se cifran con AES-GCM-256 usando nonces únicos. | Confidencialidad y protección contra replay attacks. | Escritura en almacenamiento. | `Cipher_Method == "AES-GCM-256"`. |
| **ENDO-I25** | `INV_PORT_STATIC` | Los puertos de comunicación del loop local son estáticos y parametrizados. | Evita colisiones de red con puertos efímeros del host. | Bootstrap del socket. | `Port in Allowed_List`. |
| **ENDO-I26** | `INV_TLS_FORCE` | Toda conexión entre instancias distribuidas exige TLS 1.3 con mTLS. | Protección del canal de red contra escuchas y suplantaciones. | Handshake tcp. | `TLS_Version == "1.3"`. |
| **ENDO-I27** | `INV_LIMIT_PAYLOAD`| El tamaño máximo del payload del morfismo de estado es de 10MB. | Previene desbordamientos de memoria en el Gateway. | Entrada de API. | `Payload_Size <= 10_000_000` bytes. |
| **ENDO-I28** | `INV_CORS_RESTRICT`| Las peticiones CORS están restringidas a la lista blanca de hosts locales. | Evita ejecución de scripts maliciosos desde navegadores externos. | OPTIONS response headers. | `Access-Control-Allow-Origin != "*"`.|
| **ENDO-I29** | `INV_RATE_LIMIT` | Límite estricto de peticiones por segundo en el API Gateway del morfismo. | Protección contra denegación de servicio por subagentes. | Ingesta de peticiones. | `Requests_Per_Second <= 50`. |
| **ENDO-I30** | `INV_MIME_CHECK` | Los payloads de comunicación se transmiten estrictamente en JSON tipado. | Previene fallos en el parser de esquemas de FastAPI. | Header de petición. | `Content-Type == "application/json"`.|
| **ENDO-I31** | `INV_VERSION_CHECK`| El receptor rechaza morfismos emitidos por versiones de código no alineadas. | Evita corrupción del Ledger por incompatibilidad de clases. | Cabecera HTTP parseada. | `Client_Version == Server_Version`.|
| **ENDO-I32** | `INV_ERROR_CLEAN` | Las respuestas HTTP de error no contienen stack traces del backend. | Evita fugas de información sobre la topología física. | HTTP response body. | `contains("traceback") == False`. |
| **ENDO-I33** | `INV_ALIVE_PROBE` | El worker del endomorfismo expone endpoint de liveness `/health` local. | Monitorización de caída silenciosa del proceso. | Petición externa. | `Health_Status == 200`. |
| **ENDO-I34** | `INV_CACHE_COHER` | La caché en memoria se invalida inmediatamente al ocurrir una escritura. | Garantiza lecturas de datos actualizados. | Post-persist hook. | `Cache_Is_Dirty == True` tras write. |
| **ENDO-I35** | `INV_HOST_VERIFY` | El Gateway valida estrictamente la cabecera Host de la petición entrante. | Previene ataques de envenenamiento de DNS local. | Middleware API. | `Host_Header in Allowed_Hosts`. |
| **ENDO-I36** | `INV_PROXY_REUSE` | El proxy utiliza un pool de conexiones HTTP reutilizables. | Evita el agotamiento de sockets TCP en el SO. | Inicialización de httpx client. | `Pool_Size >= 1` (reutilización). |
| **ENDO-I37** | `INV_UVI_TIMEOUT` | El timeout de keep-alive del servidor ASGI es superior al TTL de inferencia. | Previene cierres inesperados de conexión en peticiones largas. | Configuración de Uvicorn. | `Keep_Alive_Timeout >= 60` segundos. |
| **ENDO-I38** | `INV_POISON_BLOCK`| Todo morfismo entrante se valida con la clave pública del Swarm. | Protección contra inyección de transiciones no autorizadas. | Ingesta de evento. | `Signature_Valid == True`. |
| **ENDO-I39** | `INV_COMP_BACKUP` | Se ejecuta backup inmutable de base de datos antes de una compactación. | Permite recuperación ante fallos de disco catastróficos. | Hook de mantenimiento. | `Backup_File_Exists == True`. |
| **ENDO-I40** | `INV_ENV_PROTECT` | El endomorfismo no puede modificar variables de entorno del host. | Aislamiento operativo a nivel de sistema operativo. | Evaluación en sandbox. | `Env_Modified == False`. |
| **ENDO-I41** | `INV_VEC_DEDUP`   | Los vectores de embeddings del estado no contienen registros idénticos. | Previene redundancias y degradación de búsqueda en vec0. | Commit vectorial. | `Distance(Vector_A, Vector_B) > epsilon`.|
| **ENDO-I42** | `INV_LAZY_EAGER`  | Las tareas encoladas se resuelven en un ciclo máximo de 10 iteraciones. | Evita acumulación infinita de callbacks latentes en memoria. | Monitor del event loop. | `Lazy_Queue_Depth <= 10`. |
| **ENDO-I43** | `INV_FUNCTOR_ID`  | Un functor de mapeo mapea la identidad a la identidad. | Preservación de la estructura del loop en traslación. | Validación functorial. | `F(1_X) == 1_F(X)`. |
| **ENDO-I44** | `INV_FUNCTOR_COMP`| El functor preserva la composición de morfismos. | Preservación del historial de operaciones compuesto. | Sincronización remota. | `F(f . g) == F(f) . F(g)`. |
| **ENDO-I45** | `INV_BFT_KEYS`    | Los nodos BFT firman mensajes con Ed25519 con claves únicas en Keyring. | Autenticidad innegable de los votos de consenso. | Emisión de voto. | `Signer_Key_Valid == True`. |
| **ENDO-I46** | `INV_HEISENBERG_COMM` | Los operadores de posición y momento satisfacen la relación canónica ($[x, p] = i\hbar$). | No conmutatividad de transformaciones de escala en el Heisenberg-Weyl. | Composición de operadores escalares. | `x . p - p . x == i * h_bar`. |
| **ENDO-I47** | `INV_FIBER_LIMIT` | El número de preimágenes para un estado meta está acotado. | Evita explosión de relaciones n-a-n en el grafo. | Inserción en base de datos. | `Preimages_Count <= 100` por estado. |
| **ENDO-I48** | `INV_GIT_SENTINEL`| Todo commit generado incluye el hash SHA-256 de Ledger actual. | Enlace bidireccional inquebrantable entre código y base. | Git commit trigger. | `Ledger_Hash in Commit_Message`. |
| **ENDO-I49** | `INV_SHANNON_MAX` | El texto persistido debe tener una entropía superior al umbral mínimo. | Excluye alucinaciones vacías y respuestas enlatadas. | Fact commit block. | `Shannon_Entropy >= 1.5` bits. |
| **ENDO-I50** | `INV_APOP_TRIGGER`| El trigger de apoptosis mata el proceso en caso de violación de invariantes. | Evita la persistencia de estados rotos o corrompidos. | Excepción crítica en Guard. | `Apoptosis_Fired == True` en fallo. |
"""

# ==========================================
# 4. INVARIANTES 51-100
# ==========================================
invariantes_51_100_content = r"""# ONTOLOGY-FORGE-OMEGA: ENDOMORFISMO INVARIANTES (BATCH 2)
**Dominio:** Endomorfismos en sistemas agénticos, teoría de categorías aplicada a la autopoiesis y composición de loops reflexivos.
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 2.1: 50 INVARIANTES ADICIONALES DE COHERENCIA (ENDO-I51..100)
Ampliación de las leyes inmutables de preservación de consistencia, control de concurrencia y seguridad en transformaciones de estado.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **ENDO-I51** | `INV_LOOP_RESOLV` | Las corrutinas del loop reflexivo deben ceder control periódicamente. | Previene congelamientos del event loop del Gateway. | Ejecución asíncrona de morfismo. | `Time_Between_Yields <= 100` ms. |
| **ENDO-I52** | `INV_HOM_SET_CAP` | El número de morfismos distintos en un objeto está acotado. | Previene desbordamiento de memoria por meta-conocimiento. | Indexado semántico en base. | `len(Hom(X, X)) <= 10_000`. |
| **ENDO-I53** | `INV_EIGEN_VAL_OK`| Los autovalores del sistema de transiciones están en el rango (-1, 1). | Garantiza convergencia y estabilidad a largo plazo. | Multiplicación matricial. | `abs(Eigenvalues) < 1.0`. |
| **ENDO-I54** | `INV_FUNCTOR_DET` | El mapeo functorial es determinista y no depende de variables de red. | Evita inconsistencias de transiciones entre entornos. | Mapeo inter-sistema. | `F(f, State) == Constant` en t. |
| **ENDO-I55** | `INV_EIGEN_DIM`   | El espacio vectorial de embeddings mantiene su dimensionalidad estática. | Previene colisiones por mezcla de modelos en vec0. | Inserción vectorial. | `Vector_Dimension == 1536` o 768. |
| **ENDO-I56** | `INV_MONOID_UNIT` | La identidad `1_X` es única para cada conjunto de endomorfismos. | Previene inicializaciones ambiguas del loop. | Carga inicial del sistema. | `len(Identity_Elements) == 1`. |
| **ENDO-I57** | `INV_SCHED_FIFO`  | Las tareas del cron se ejecutan en orden estrictamente temporal. | Previene condiciones de carrera por reordenamiento. | Encolador de tareas. | `Execution_Order == Sorted_Timestamp`.|
| **ENDO-I58** | `INV_LOG_EXERGY`  | Los logs de traza contienen estrictamente información estructurada. | Evita desperdicio de tokens en almacenamiento local. | Logger output check. | `contains("slop") == False`. |
| **ENDO-I59** | `INV_SANDBOX_NET` | El sandbox de ejecución tiene deshabilitado el acceso a red externa. | Evita exfiltración de datos sensibles durante JIT compilation. | Configuración de sandbox. | `Network_Connections_Allowed == False`.|
| **ENDO-I60** | `INV_MIG_ROLLBACK`| Todo script de migración expone obligatoriamente ruta de rollback. | Permite recuperación de estado ante fallos de despliegue. | Declaración de migración. | `hasattr(Migration, "down") == True`.|
| **ENDO-I61** | `INV_FD_LIMIT`    | El loop de composición no puede exceder el 80% de descriptores de archivos del host. | Previene caídas catastróficas por saturación del SO. | Bootstrap del socket. | `Open_FDs < 0.8 * Max_FDs`. |
| **ENDO-I62** | `INV_ISOM_PAIR`   | El morfismo inverso `f_inv` se genera y actualiza atómicamente con `f`. | Evita estados intermedios no reversibles en SAGA-6. | Mutación de clases de lógica. | `hasattr(f, "inverse") == True`. |
| **ENDO-I63** | `INV_RAM_GC`      | La memoria RAM del worker se libera explícitamente tras cada ciclo. | Evita OOM en ejecuciones prolongadas de swarm. | Hook post-ejecución. | `RAM_Usage_After_GC <= Basal_Limit`. |
| **ENDO-I64** | `INV_EPIST_RECON` | Dos verdades conflictivas inician reconciliación automatizada. | Evita bloqueos epistémicos o loops de parálisis. | Guard check de coherencia. | `Reconciliation_Active == True`. |
| **ENDO-I65** | `INV_TAINT_DEEP`  | La copia de morfismos de estado debe realizarse vía deepcopy. | Conserva metadatos de taint originales y previene desvío. | Copia de clases de estado. | `id(State_In.taint) != id(State_Out.taint)`.|
| **ENDO-I66** | `INV_GIT_CLEAN`   | El working tree del repositorio debe estar limpio antes de transicionar. | Previene contaminación de commits con archivos huérfanos. | Pre-commit hook validation. | `git_status == "clean"`. |
| **ENDO-I67** | `INV_CHAOTIC_LIM` | La divergencia de autovectores en loops está limitada por exponente de Lyapunov. | Garantiza predictibilidad matemática del sistema. | Simulación dinámica. | `Lyapunov_Exponent <= Threshold`. |
| **ENDO-I68** | `INV_NIL_TRANS`   | El estado nilpotent nulo no puede ser el destino final del flujo principal. | Evita colapso absoluto del sistema a estado cero. | Verificación de parada. | `Final_State != 0`. |
| **ENDO-I69** | `INV_IDEM_GRAD`   | Las transiciones deben aportar un delta exérgico neto mayor que cero. | Previene parálisis del loop en estados idempotentes. | Evaluación en runtime. | `Exergy_Yield > 0` en composición. |
| **ENDO-I70** | `INV_COHOM_DET`   | Los ciclos de cohomología están cerrados y validados criptográficamente. | Garantiza coherencia distributiva sin bucles huérfanos. | Swarm status verification. | `verify_cohomology() == True`. |
| **ENDO-I71** | `INV_AUT_EVOLVE`  | El loop de automorfismos debe acoplarse con inyección de inputs externos. | Previene ciclos cerrados estériles sin aprendizaje. | Ingesta de memoria. | `Inputs_Processed > 0` en t. |
| **ENDO-I72** | `INV_KEY_SECURE`  | La clave de cifrado se aloja en almacenamiento de llavero del SO local. | Evita exposición de secretos en archivos de configuración. | Keyring check. | `Key_Source == "OS_Keyring"`. |
| **ENDO-I73** | `INV_DB_CONCUR`   | SQLite opera estrictamente con `busy_timeout` fijado en 5000ms. | Previene deadlocks por colisiones de escritura concurrentes. | DB initialization helper. | `busy_timeout == 5000`. |
| **ENDO-I74** | `INV_COLIM_BOUND` | El colímite de la base está acotado a 1 millón de registros vectoriales. | Previene degradación de rendimiento en vec0. | DB insertion hook. | `Total_Records <= 1_000_000`. |
| **ENDO-I75** | `INV_SENTINEL_OK` | El Git Sentinel valida el hash Ledger en cada commit local. | Evita desincronizaciones de base de datos inter-sesión. | Git commit verification. | `Verify_Sentinel_Hash() == True`. |
| **ENDO-I76** | `INV_ENTROPY_MIN` | Las respuestas conservan un nivel mínimo de Shannon en base a tokens únicos. | Filtra outputs simplistas de baja exergía. | Cortex vault commit filter. | `Shannon_Entropy >= 1.2` bits. |
| **ENDO-I77** | `INV_STACK_YIELD` | Las funciones recursivas de morfismos ejecutan un yield cada 5 niveles. | Previene desbordamiento de pila física del runtime. | Intérprete check. | `Recursion_Depth_Since_Yield <= 5`. |
| **ENDO-I78** | `INV_KEY_MEMORY`  | Las llaves de cifrado en memoria volátil se purgan tras el uso. | Previene extracción de claves vía volcados de memoria (dump). | Cryptography wrapper. | `Memory_Cleared == True` post-decrypt. |
| **ENDO-I79** | `INV_MUTEX_BLOCK` | Todo lock de recurso compartido expone un timeout de resolución máximo de 1s. | Previene bloqueos mutuos permanentes. | Lock request logic. | `Lock_Timeout <= 1000` ms. |
| **ENDO-I80** | `INV_BFT_QUORUM`  | Los mensajes de consenso BFT se transmiten firmados por al menos 2/3 nodos. | Previene ataques Sybil y desviaciones de Ledger. | Consensual commit step. | `Signers_Count >= (2/3) * N_Nodes`. |
| **ENDO-I81** | `INV_FASTAPI_VAL` | FastAPI utiliza validadores Pydantic estrictos en todos los payloads. | Previene inyección de payloads deformados al backend. | Endpoint function definition. | `hasattr(endpoint, "pydantic_model")`.|
| **ENDO-I82** | `INV_PORT_CHECK`  | El script de bootstrap valida que el puerto de red está libre antes de levantar. | Evita colisiones de puertos con servicios zombies. | Server startup utility. | `Port_Is_Free == True`. |
| **ENDO-I83** | `INV_CONN_RETRY`  | Los reintentos de conexión inter-agente emplean algoritmo de backoff con jitter. | Previene colapso del Gateway por thundering herd. | Http client helper. | `Retry_Method == "Backoff_With_Jitter"`.|
| **ENDO-I84** | `INV_GATEWAY_CAP` | El Gateway limita el tamaño máximo de los campos JSON a 1MB. | Previene desbordamientos de buffer por inyección. | FastAPI request limits. | `Max_Field_Size <= 1_000_000` bytes. |
| **ENDO-I85** | `INV_CORS_STRICT` | Las cabeceras CORS en producción excluyen explícitamente el wildcard asterisco. | Previene ataques de scripting malicioso. | API configuration middleware. | `CORS_Wildcard == False`. |
| **ENDO-I86** | `INV_LIMIT_BLOCK` | Peticiones que exceden el rate limit son bloqueadas por 60 segundos. | Previene ataques de fuerza bruta. | Rate limiter filter. | `Ban_Duration == 60` segundos. |
| **ENDO-I87** | `INV_TLS_CIPHER`  | Se exige TLS 1.3 con suite de cifrado AES-256-GCM en el socket. | Garantiza protección del canal ante ataques criptográficos modernos. | TLS connection handshake. | `Cipher_Suite == "AES-256-GCM"`. |
| **ENDO-I88** | `INV_VER_COMPAT`  | Las API del morfismo son compatibles retroactivamente hasta un nivel menor (Minor). | Evita rupturas del sistema durante actualizaciones parciales. | API gateway validation middleware. | `Client_Minor_Ver >= Required_Minor`.|
| **ENDO-I89** | `INV_CLEAN_ERR`   | El Gateway devuelve JSON estructurado de error sin rutas físicas legibles. | Evita exposición de directorios del host. | Exception handler global. | `Physical_Paths_In_Response == 0`. |
| **ENDO-I90** | `INV_MONITOR_RUN` | El daemon de watchdog se ejecuta como proceso independiente del host. | Garantiza monitorización persistente e inmune a fallas de API. | Watchdog script check. | `Watchdog_PID_Active == True`. |
| **ENDO-I91** | `INV_CACHE_REDIS` | El almacenamiento Redis L1 cache tiene TTL máximo de 300 segundos. | Previene consistencia degradada por caché obsoleta prolongada. | Redis client instantiation. | `Default_TTL <= 300` segundos. |
| **ENDO-I92** | `INV_HOST_WHITE`  | El proxy local del morfismo sólo enruta peticiones a dominios de lista blanca. | Previene desvío de tráfico sensible a redes externas. | API Gateway routing table. | `Target_Domain in Whitelist`. |
| **ENDO-I93** | `INV_ASYNC_POOL`  | El cliente httpx utiliza un único pool de conexiones cerrado. | Evita el consumo desmedido de descriptores de socket TCP. | API gateway client helper. | `Pool_Closed == True` on app exit. |
| **ENDO-I94** | `INV_ASGI_TIMEOUT`| Uvicorn timeout keep-alive está configurado a 15 segundos en local. | Minimiza retención de sockets inactivos. | ASGI command run execution. | `keep_alive_timeout == 15`. |
| **ENDO-I95** | `INV_MIME_STRICT` | El parser rechaza cualquier payload que no declare Content-Type válido. | Previene inyecciones de payloads deformados. | API Gateway entry validation. | `Header_Content_Type == Required`. |
| **ENDO-I96** | `INV_SIGN_MT`     | Todo mensaje inter-agente incluye la firma digital Ed25519 del emisor. | Garantiza autenticidad y previene suplantación de nodos. | Message serialization handler. | `hasattr(Message, "Signature")`. |
| **ENDO-I97** | `INV_MIG_LEDGER`  | Las migraciones de esquema emiten un evento criptográfico al Ledger. | Registra la trazabilidad del cambio de estructura. | Database migration execution. | `Ledger_Event_Logged == True`. |
| **ENDO-I98** | `INV_INVAR_FILE`  | Los archivos de configuración invariantes se montan en modo lectura en el Docker/SO. | Previene modificaciones accidentales de directivas. | Container execution configuration. | `Mount_Mode == "read_only"`. |
| **ENDO-I99** | `INV_VEC_STRICT`  | SQLite-Vec exige concordancia de dimensiones del vector en cada query. | Evita fallas catastróficas de comparación. | SQLite query build. | `Query_Vector_Dimension == DB_Dim`. |
| **ENDO-I100**| `INV_LAZY_CLEAN`  | Las colas de tareas lazy se purgan por completo al detener el worker. | Previene persistencia de tareas huérfanas en el reinicio. | Shutdown lifecycle hook. | `Lazy_Queue_Depth == 0` on stop. |
"""

# ==========================================
# 5. ESTRUCTURAL: ANTIPATRONES, REDUNDANCIAS, RED ALERTS
# ==========================================
estructural_content = r"""# ONTOLOGY-FORGE-OMEGA: ESTRUCTURAS DE RESILIENCIA Y AMENAZAS (ENDOMORFISMO)
**Dominio:** Endomorfismos en sistemas agénticos, teoría de categorías aplicada a la autopoiesis y composición de loops reflexivos.
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 3: 20 ANTIPATRONES ESTOCÁSTICOS (ENDO-AP01..20)
Decisiones de diseño y patrones erróneos que inyectan fragilidad, loops infinitos o degradación de información en composiciones de estado.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **ENDO-AP01** | **Circular Dependency Loop** | Composición de endomorfismos cíclicos sin control de corte (Circuit Breaker). | Recursión infinita en logs sin yields. | Desborde de pila (StackOverflow) y OOM. | Implementar contador Max-Hops y apoptosis. |
| **ENDO-AP02** | **Anergy Prose Gate** | Intentar describir el morfismo de transformación en prosa dentro del loop. | Tokens de explicación en base de datos. | Desperdicio de tokens y degradación de exergía. | Epistemic-Purge-OMEGA y colapso directo a Hash. |
| **ENDO-AP03** | **Unsigned Hot Patching** | Mutar el estado interno saltándose el Write-Path Contract y la firma Taint. | Registros SQLite sin metadatos de taint. | Pérdida de proveniencia y auditoría rota. | Forzar `CORTEX-TAINT` en cada INSERT/UPDATE. |
| **ENDO-AP04** | **Wildcard CORS Route** | Levantar la API local del morfismo con políticas CORS abiertas (`*`). | Asterisco visible en la configuración de CORS. | Exfiltración de estados a través de XSS. | Restringir CORS estrictamente a localhost. |
| **ENDO-AP05** | **Mixed Socket Context** | Compartir el mismo puerto de red para flujos TLS y flujos en texto plano. | Ausencia de canal TLS forzado en el endpoint. | Intercepción de estados sensibles (MitM). | Forzar puertos y certificados segregados. |
| **ENDO-AP06** | **Nostalgic Sync Blocking**| Usar llamadas I/O síncronas (`time.sleep`) en loops recursivos asíncronos. | `def` en rutas ordinarias en lugar de `async def`. | Congelamiento completo de la API del Gateway. | Refactorizar a corrutinas asíncronas nativas. |
| **ENDO-AP07** | **Parametric Hallucination**| Confiar en la memoria implícita del modelo para transiciones sin verificar en disco. | Morfismo generado sin fuentes locales. | Desviación de lógica y código malicioso. | Ley de Proveniencia Obligatoria (AX-041). |
| **ENDO-AP08** | **Loose Identity Morp** | Asumir que la identidad `1_X` no necesita validación explícita. | Mutación accidental de estado en bootstrap. | Estado inicial corrompido en frío. | Validar identidad con test unitario en inicio. |
| **ENDO-AP09** | **Vector Dimension Mix** | Mezclar vectores de embeddings de diferentes modelos en la tabla vec0. | Fallas de distancia de coseno en SQLite-Vec. | Búsqueda semántica rota o degradada. | Separar tablas virtuales por modelo de embedding. |
| **ENDO-AP10** | **Untracked DB Migrat** | Modificar esquemas de SQLite sin registrar scripts de migración. | Base de datos malformada en CI. | Ruptura de consistencia en despliegues. | migrar vía `migrate.py` y registrar en git. |
| **ENDO-AP11** | **Ghost Working Tree** | Dejar archivos temporales sin registrar en git en el directorio del loop. | Working tree sucio en CI. | Loops de commit infinitos en pre-commit. | Excluir temporales en `.git/info/exclude`. |
| **ENDO-AP12** | **Plaintext Key Storage** | Almacenar claves de cifrado en variables del entorno o JSON de config. | Claves legibles en repositorios. | Compromiso total del cifrado de estados. | Integrar llavero del sistema operativo (Keyring).|
| **ENDO-AP13** | **Unbounded Task Queue** | Acumular tareas perezosas en el event loop sin límite de encolamiento. | Crecimiento incontrolado de memoria RAM. | Caída del Gateway por OOM. | Forzar resolución ansiosa y paginado. |
| **ENDO-AP14** | **Bare Exceptions Catch** | Capturar excepciones genéricas (`except Exception:`) en core paths. | Silenciamiento de bugs críticos. | Corrupción silenciosa del Ledger. | Capturar excepciones específicas. |
| **ENDO-AP15** | **Dynamic Route Eval** | Ejecutar código de ruteo dinámico sin validación criptográfica previa. | Inserción directa de rutas desde payloads JSON. | Secuestro de tráfico por workers maliciosos. | Tabla de ruteo inmutable y firmada. |
| **ENDO-AP16** | **Stack Exposure Err** | Retornar stack traces legibles en el JSON de respuesta HTTP de error. | Stack trace en responses HTTP 500. | Fugas de directorios y vulnerabilidades físicas. | Middleware limpio de excepciones. |
| **ENDO-AP17** | **Zombie Sockets Host**| Cerrar el proceso principal del morfismo sin liberar los sockets locales. | Address already in use error en bootstrap. | Imposibilidad de reiniciar el Gateway. | Shutdown hooks de cierre ordenado. |
| **ENDO-AP18** | **Cold Cache Read** | Leer el estado del morfismo desde caché L1 fría sin invalidación activa. | Datos obsoletos leídos por subagente. | Divergencia de estado lógica. | Invalidador síncrono post-persist. |
| **ENDO-AP19** | **DNS Poison Tunnel** | Configurar el proxy local para que acepte cualquier cabecera Host. | Peticiones locales redirigidas a internet. | Fuga de estados locales a atacantes. | Middleware de Host de lista blanca. |
| **ENDO-AP20** | **Mime Type Ignorance**| Ignorar la validación de cabecera Content-Type en peticiones HTTP entrantes. | FastAPI retorna error 415. | Rupturas de parser y excepciones no capturadas. | Validar Content-Type obligatoriamente. |

---

## MATRIZ 4: 10 REDUNDANCIAS ACTIVAS (ENDO-RA01..10)
Mecanismos de aislamiento, duplicación y tolerancia a fallas en transformaciones reflexivas de estado.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **ENDO-RA01** | **BFT Consensus Swarm** | Quórum de N=3 validadores para firmar transiciones de estado del morfismo. | Fallos bizantinos de workers locales. | 3x tiempo de procesamiento. | `cortex/consensus/` |
| **ENDO-RA02** | **Dual Reverse Proxy** | Servidores de balanceo locales (Nginx/Uvicorn) en redundancia activa. | Caída o bloqueo del event loop ASGI. | Consumo mínimo de memoria. | Nginx local. |
| **ENDO-RA03** | **Git Sentinel Ledger** | Vinculación del Ledger con el historial inmutable del repositorio Git (DAG). | Alteración de base de datos offline. | Mínimo en cada commit. | Git CLI. |
| **ENDO-RA04** | **Volatile Sandbox** | Creación y destrucción de sandboxes de ejecución para JIT compilaciones. | Escalada de privilegios y compromisos. | Tiempo de bootstrap. | Docker o jail local. |
| **ENDO-RA05** | **Fallback DNS Hosts** | Resolución local estática de IPs en `/etc/hosts` de la máquina. | Caída del servidor de nombres externo. | Ninguno. | Permisos de lectura. |
| **ENDO-RA06** | **Backup Gateway Node**| Servidor local de fallback escuchando en puerto secundario. | Puerto principal bloqueado o Zombie. | Duplicidad de puertos. | FastAPI local. |
| **ENDO-RA07** | **Epistemic Purge L1** | Caché L1 con invalidación proactiva y limpieza de anergía en memoria. | Consistencia degradada por caché obsoleta. | Latencia de invalidador. | Redis local. |
| **ENDO-RA08** | **Taint Signature Seal**| Generación de SHA3-256 de payload integrado con metadatos de procedencia. | Mutaciones de estado anónimas. | Criptográfico por bloque. | `taint_engine.py` |
| **ENDO-RA09** | **Keyring OS Escrow** | Custodia de claves de cifrado en el llavero seguro del sistema operativo. | Robo de claves en disco duro local. | MS de llamada. | API de Keyring. |
| **ENDO-RA10** | **compaction Backup** | Clonación inmutable de la base de datos previa a la purga y compactación. | Corrupción catastrófica de SQLite. | Espacio en disco. | aiosqlite utilities. |

---

## MATRIZ 5: 10 VECTORES DE ATAQUE ADVERSARIAL / RED ALERTS (ENDO-AV01..10)
Técnicas de inyección de entropía, denegación y corrupción dirigidas a loops reflexivos y morfismos.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **ENDO-AV01** | **Infinite Recursion Attack** | Stack del runtime local. | Inyección de payload recursivo infinito ($f^n(x)$) sin yield asíncrono. | StackOverflow / Caída del proceso. | `ENDO-I77` (Stack Yield) y Circuit Breaker. |
| **ENDO-AV02** | **Taint Stripping Exploit** | Cabeceras de la API. | Envío de peticiones de mutación eliminando o alterando el taint. | Corrupción del Ledger sin rastros. | Bloqueo estricto Write-Path (SAGA-2). |
| **ENDO-AV03** | **Identity Spoofing** | Identidad del monoide. | Modificación del morfismo identidad $1_X$ para redirigir transiciones. | Ruptura de consistencia en frío. | Validar identidad antes de operar. |
| **ENDO-AV04** | **Parameter Fuzzing** | Endpoints de FastAPI. | Envío masivo de payloads JSON deformados para romper el tipado. | Exposición de stack trace (500). | Tipado estricto Pydantic y try-catch. |
| **ENDO-AV05** | **Origin Hijack CORS** | Cabecera Origin HTTP. | Simulación de origen permitido desde navegadores externos atacantes. | Ejecución de transiciones cruzadas. | CORS restrictivo acotado a localhost. |
| **ENDO-AV06** | **Slowloris Sockets** | Servidor ASGI Uvicorn. | Mantener conexiones HTTP abiertas indefinidamente con bytes lentos. | Agotamiento de descriptores de red. | Timeout de keep-alive estricto en Uvicorn. |
| **ENDO-AV07** | **Topology Flood** | Grafo de ruteo del Swarm. | Enviar miles de cambios de topología falsificados. | Colapso de tablas de ruteo locales. | Firmas BFT requeridas en topology checks. |
| **ENDO-AV08** | **Replay Token Attack** | Endpoint de autenticación. | Reinyectar token firmado capturado dentro de la ventana de 5s. | Ejecución de transiciones no autorizadas.| Timestamp estricto y nonces únicos. |
| **ENDO-AV09** | **Key Extraction Dump** | Memoria RAM del host. | Volcado de memoria RAM para extraer llaves de cifrado en reposo. | Compromiso total del cifrado de estados. | Purgar claves tras uso en memoria. |
| **ENDO-AV10** | **Environment Poisoning** | Variables de entorno del host. | Inyectar variables de entorno falsas para desviar el proxy local. | Redirección de datos a servidor externo. | Cuarentena estricta de variables del host. |

SYS_ID borjamoskv
"""

# Guardar archivos
with open(os.path.join(ontology_dir, "endomorfismo_primitivas_01.md"), "w") as f:
    f.write(primitivas_01_50_content)

with open(os.path.join(ontology_dir, "endomorfismo_primitivas_02.md"), "w") as f:
    f.write(primitivas_51_100_content)

with open(os.path.join(ontology_dir, "endomorfismo_invariantes_01.md"), "w") as f:
    f.write(invariantes_01_50_content)

with open(os.path.join(ontology_dir, "endomorfismo_invariantes_02.md"), "w") as f:
    f.write(invariantes_51_100_content)

with open(os.path.join(ontology_dir, "endomorfismo_estructural.md"), "w") as f:
    f.write(estructural_content)

print("[C5-REAL] Todos los archivos de la ontología Endomorfismo guardados con éxito.")

# ----------------- PARSER Y COMPILADOR A JSON/YAML -----------------
import json
import yaml

def parse_markdown_tables(filepath):
    all_tables = []
    current_table = []
    headers = []
    in_table = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                if in_table and current_table:
                    all_tables.append(current_table)
                    current_table = []
                in_table = False
                headers = []
                continue
            if "---" in line or "|:---" in line:
                continue
            cells = [cell.strip().replace("**", "").strip("`").strip() for cell in line.split("|")[1:-1]]
            if not in_table:
                headers = cells
                in_table = True
            else:
                entity = dict(zip(headers, cells, strict=False))
                if entity.get("ID") and entity["ID"].startswith("ENDO-"):
                    current_table.append(entity)
        if in_table and current_table:
            all_tables.append(current_table)
    return all_tables

print("[C5-REAL] Compilando ontología Endomorfismo en JSON y YAML...")

primitivas = parse_markdown_tables(os.path.join(ontology_dir, "endomorfismo_primitivas_01.md"))[0] + \
             parse_markdown_tables(os.path.join(ontology_dir, "endomorfismo_primitivas_02.md"))[0]

invariantes = parse_markdown_tables(os.path.join(ontology_dir, "endomorfismo_invariantes_01.md"))[0] + \
              parse_markdown_tables(os.path.join(ontology_dir, "endomorfismo_invariantes_02.md"))[0]

estructural_tables = parse_markdown_tables(os.path.join(ontology_dir, "endomorfismo_estructural.md"))
antipatrones = estructural_tables[0]
redundancias = estructural_tables[1]
adversariales = estructural_tables[2]

registry = {
    "M1_PRIMITIVES": primitivas,
    "M2_INVARIANTS": invariantes,
    "M3_ANTIPATTERNS": antipatrones,
    "M4_REDUNDANCIAS": redundancias,
    "M5_VECTORS": adversariales
}

output_json = os.path.join(ontology_dir, "endomorfismo_ontology.json")
output_yaml = os.path.join(ontology_dir, "endomorfismo_ontology.yaml")

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

with open(output_yaml, "w", encoding="utf-8") as f:
    yaml.dump(registry, f, allow_unicode=True, sort_keys=False)

print(f"[C5-REAL] Ontología compilada con éxito: {len(primitivas)}P + {len(invariantes)}I + {len(antipatrones)}AP + {len(redundancias)}RA + {len(adversariales)}AV.")

