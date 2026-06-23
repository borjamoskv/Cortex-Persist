# AUTODIDACT-RESEARCH-Ω: 100 Primitivas Ejecutables de un Ingeniero Senior Cum Laude

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Ingesta termodinámica de las 100 primitivas fundacionales de ingeniería APEX.
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
El estado epistémico del Ingeniero APEX no se rige por cantidad de herramientas, sino por la aniquilación de la entropía. Cada primitiva opera bajo el principio de Cero Anergía y Mínima Acción Computacional. Se cristalizan aquí las leyes físicas de la ejecución determinista de software.

---

## 1.5 Las Primitivas de Máxima Exergía para la Mitigación / Ejecución

### FÍSICA COMPUTACIONAL Y TERMODINÁMICA
- **APEX-001**: `Principio de Landauer` - Borrar información es el único coste termodinámico real.
- **APEX-002**: `Cero Anergía` - Toda línea de código que no muta estado o evalúa una regla matemática es basura.
- **APEX-003**: `Límite de Shannon` - Reconocer la entropía máxima de un canal antes de intentar comprimir su señal.
- **APEX-004**: `Isomorfismo Estructural` - Alinear la topología de la estructura de datos con la topología del problema real.
- **APEX-005**: `Grafo de Dependencia (DAG)` - El tiempo fluye en una dirección; evitar ciclos lógicos a toda costa.
- **APEX-006**: `Minimización de Estados` - Cada variable de estado temporal multiplica exponencialmente el espacio de fallos.
- **APEX-007**: `Determinismo Físico` - El mismo input produce idéntico output invariablemente, o el sistema está termodinámicamente roto.
- **APEX-008**: `Apoptosis de Código` - Destruir código rutinariamente para mantener el organismo vivo y esbelto.
- **APEX-009**: `Carga Cognitiva Acotada` - El código de un módulo debe caber íntegramente en la memoria de trabajo (L1) del cerebro humano.
- **APEX-010**: `Fricción por Diseño` - Inyectar fricción matemática a las operaciones destructivas (Rate limits, idempotencia dura, 2FA).

### MUTACIÓN DE ESTADO Y CAUSALIDAD
- **APEX-011**: `Inmutabilidad por Defecto` - Mutar estado local solo cuando es termodinámicamente ineludible.
- **APEX-012**: `Integridad Merkle` - Usar hashes criptográficos encadenados para verificar la validez histórica de estados completos.
- **APEX-013**: `Idempotencia Rigurosa` - Ejecutar un commit 1000 veces tiene el mismo side-effect en el universo físico que ejecutarlo 1 vez.
- **APEX-014**: `Atomicidad Absoluta (ACID)` - Todo colapsa a la vez o nada muta. Cero estados intermedios parcialmente sucios.
- **APEX-015**: `Event-Sourced Append-Only` - La base de datos causal es el Log inmutable; las tablas relacionales son solo proyecciones temporales en caché.
- **APEX-016**: `Trazabilidad Causal` - Todo bit en persistencia debe poder rastrearse hasta el token o aserción que autorizó su generación.
- **APEX-017**: `Versionado Epistémico` - Nunca alterar semánticamente un campo existente de un API o DB; se deprecia y se crea uno nuevo (V2).
- **APEX-018**: `Desacoplamiento de Relojes` - Nunca depender del reloj del sistema OS para secuenciación de eventos. Usar Relojes de Lamport.
- **APEX-019**: `Cierre Optimista (CAS)` - Asumir colisión nula, pero forzar validación de versión atómica (Compare-and-Swap) en el momento del commit.
- **APEX-020**: `Taint-Tracking` - Tratar toda entrada externa como biológicamente contaminada (TAINTED) hasta que un validador determinista la purifique.

### ARQUITECTURA AISLADA
- **APEX-021**: `Core Hexagonal Puro` - El dominio matemático de la aplicación ignora la existencia del disco, la red o el framework web.
- **APEX-022**: `Límites Bounded-Context` - El modelo de datos Usuario en Facturación es un nodo completamente desconectado del Usuario de Autenticación.
- **APEX-023**: `Inversión de Control (IoC)` - La lógica invoca a los inyectores; el núcleo de dominio no hereda jamás clases de infraestructura.
- **APEX-024**: `Fallback Degradado` - Si falla el subsistema primario, decaer a heurística en memoria; si falla heurística, decaer a valor estático de supervivencia.
- **APEX-025**: `Coreografía de Dominio` - Emitir eventos tras mutar estado en lugar de invocar comandos directos a otros microservicios.
- **APEX-026**: `Backpressure Explícito` - Si un buffer se satura, soltar paquetes inmediatamente y fallar duro. No acumular latencia infinita en memoria.
- **APEX-027**: `Fail-Fast (Pánico Temprano)` - Si falta una variable de entorno de credenciales, el binario debe abortar el arranque en T=0, no explotar en ejecución.
- **APEX-028**: `Estrangulamiento de Monolitos` - Refactorizar interceptando el routing de red en lugar de inyectar parches sucios en código legacy.
- **APEX-029**: `Stateless Hiding` - Empujar el estado al cliente (JWT) o al disco (Redis/DB). Los contenedores de ejecución deben ser 100% fungibles y efímeros.
- **APEX-030**: `Inyección de Realidad Física` - Benchmarking empírico. Medir latencia de I/O antes de elegir microservicios vs invocación de librería local.

### RESILIENCIA Y TOLERANCIA
- **APEX-031**: `Circuit Breakers Físicos` - Romper el circuito temporalmente cuando el upstream falla para protegerlo y evitar peticiones colgadas en red.
- **APEX-032**: `Timeouts Inflexibles` - Toda llamada que salga del proceso (Network/Disk) requiere un límite temporal innegociable inyectado en el OS.
- **APEX-033**: `Retries con Jitter` - Todo reintento en red requiere delay exponencial más ruido pseudoaleatorio para evitar Thundering Herds contra el servidor caído.
- **APEX-034**: `Chaos Engineering` - Extinguir procesos y contenedores aleatoriamente en producción para demostrar que la arquitectura realmente sana sola.
- **APEX-035**: `Tolerancia Bizantina (BFT)` - Asumir que actores dentro del propio clúster pueden haber sido comprometidos o mentir en el payload.
- **APEX-036**: `Defensa Multicapa` - Superposición de guardias. Si el atacante burla el API Gateway, choca contra las políticas de row-level security de la BD.
- **APEX-037**: `Shedding de Carga` - Destruir tráfico HTTP de background/análisis cuando el uso de CPU entra en umbrales de colapso térmico.
- **APEX-038**: `Redundancia Asimétrica` - El sistema de desastre/backup no comparte las mismas primitivas tecnológicas (ni proveedor de nube) que la región primaria.
- **APEX-039**: `Death Switches` - Cron jobs de supervivencia que alertan solo cuando fallan en realizar su ping rutinario de vida.
- **APEX-040**: `Aislamiento Control/Datos` - El plano que rutea infraestructura o configura llaves no puede nunca parsear el payload de los usuarios.

### CONCURRENCIA Y MEMORIA
- **APEX-041**: `Data Locality (L1/L2 Cache)` - Estructurar arrays de structs en memoria contigua para aplastar el coste de los Cache Misses.
- **APEX-042**: `Pipes Zero-Copy` - Pasar handles de descriptores de archivo en lugar de clonar bytes masivos al transferir a nivel de sockets (mmap, sendfile).
- **APEX-043**: `Falsa Compartición Térmica` - Padding de estructuras de datos críticas para que no compartan líneas de caché L1 entre hilos concurrentes.
- **APEX-044**: `Arenas de Memoria` - Alocar memoria en bloques unificados y matar millones de nodos descartando un solo puntero.
- **APEX-045**: `Flujos Lock-Free` - Usar variables atómicas y algoritmos de validación en lugar de Mutex bloqueantes que congelan el procesador en multi-core.
- **APEX-046**: `Actor Model (Single Writer)` - Mutar el estado interno encolando eventos hacia un solo hilo de ejecución propietario. Erradica contención compartida.
- **APEX-047**: `Batching Dinámico` - Ajustar algoritmos para agrupar buffers (batch) inversamente proporcional a la latencia de ingestión.
- **APEX-048**: `Compresión Activa en Frío` - Comprimir estado RAM inactivo (LZ4/Zstd) para liberar bloques; la CPU libre rinde mejor que invocar swap en disco.
- **APEX-049**: `Keyset Pagination Invertida` - Nunca usar OFFSET N. Usar cursores de id secuencial para garantizar accesos de índice O(log N).
- **APEX-050**: `Parseo Directo Ciego (AST)` - Nunca usar deserialización polimórfica ni evaluar strings estocásticos (eval). Mapeo crudo a bytes en structs explícitas.

### OBSERVABILIDAD Y TELEMETRÍA
- **APEX-051**: `Trazado de Causalidad Distribuida` - Inyectar cabeceras X-Trace-Id en los bordes y arrastrarlas hasta la persistencia y log de cada capa.
- **APEX-052**: `SLIs Client-Centric` - Medir latencia y error en el edge del navegador/cliente; lo que reporte el servidor interno es secundario.
- **APEX-053**: `Logs Estructurados C5` - Cero prosa decorativa. JSONL inyectable a vectores y motores analíticos de alta velocidad.
- **APEX-054**: `Alertas de Burn-Rate` - Ignorar picos temporales; alertar matemáticamente si el presupuesto de error garantizado (Error Budget) está cayendo a velocidad terminal.
- **APEX-055**: `Continuous Profiling` - Utilización de eBPF en producción de bajo overhead para observar allocs y uso de kernel sin alterar la compilación.
- **APEX-056**: `ContextVars Invisibles` - Transportar el tenant_id y las credenciales de autorización asíncrona inyectadas en la rama del Call Stack.
- **APEX-057**: `Aislamiento de Telemetría` - El cluster de métricas y alarmas debe residir en otra red, para no caer junto con el clúster de producción.
- **APEX-058**: `Sondeo en Vivo Seguro` - Inyección dinámica de puntos de captura de estado (DTrace) para extraer memoria local de funciones sin matar el host.
- **APEX-059**: `Silenciamiento de Falsos Positivos` - Si un aviso del sistema despierta al operador pero no exige acción de remediación, el log se reclasifica o silencia.
- **APEX-060**: `Semántica de Transacción C5` - Monitorear transferencias económicas, confirmaciones y latencias en dinero real, en lugar de métricas de hardware aisladas.

### DEFENSA Y CRIPTOGRAFÍA
- **APEX-061**: `Zero-Trust Físico` - Autenticación mutua (mTLS) en todas las llamadas intra-clúster. Redes privadas locales asumidas estocásticamente vulneradas.
- **APEX-062**: `Privilegio de Mínima Exergía` - Usar tokens con firmas criptográficas de expiración en milisegundos y permisos asimétricos granulares.
- **APEX-063**: `Erradicación de Secretos Disco` - Enclave encriptado de SO, HSM local y RAM efímera. Las API Keys en texto plano en .env son para simulación.
- **APEX-064**: `Comandos Preparados Absolutos` - Bindings de tipos duros para Bases de Datos. Un payload de usuario es siempre vector, nunca texto ejecutable.
- **APEX-065**: `Fricción Criptográfica Frontal` - Para passwords, fuerza bruta contrarrestada por Argon2id (coste deliberado de GPU+Memoria).
- **APEX-066**: `Cifrado de Aplicación Ciega (ALE)` - Encriptar campos PII sensibles (AES-GCM) en la RAM de aplicación antes del envío a la base de datos.
- **APEX-067**: `Identificadores Temporales Seguros` - Identidad pseudoaleatoria y ordenamiento temporal inmerso (UUIDv7) blindaje directo contra ataques IDOR.
- **APEX-068**: `Sanitización al Filo del Borde` - Whitelists de regex herméticas compiladas para denegar paquetes de red anómalos en el API Gateway.
- **APEX-069**: `Compilador Inquisidor de Tipos` - Forzar fallo de Type Checker si tipos de dominio inseguro cruzan la barrera sin un casteo asertivo auditado explícito.
- **APEX-070**: `Descentralización de llaves JWT` - Identidad verificada con firmas matemáticas públicas (JWKS). Microservicios independientes nunca contactan al emisor de auth.

### OPTIMIZACIÓN Y PERFORMANCE
- **APEX-071**: `Extracción Big-O Inflexiva` - Erradicar iteraciones anidadas ocultas en frameworks ORMs O(N²); forzar hashes O(1) inyectados.
- **APEX-072**: `Filtros de Membrana Probabilística` - Criba de pertenencia inicial; denegar solicitudes O(1) de datos faltantes antes de golpear bloques de disco.
- **APEX-073**: `Poda de Árbol Primitiva` - Evaluar reglas o short-circuits binarios que descartan computaciones masivas en los primeros nanosegundos (Branch Culling).
- **APEX-074**: `SIMD Nativo (Vectorización)` - Forzar vectores e iteradores alineados para ejecutar sumas de miles de arrays en ciclos únicos de reloj (AVX/Neon).
- **APEX-075**: `Memoización Inmutable de Hashes` - Usar un hash SHA del tuple de inputs de funciones analíticas para servir memoria en vez de computar.
- **APEX-076**: `Inyección de Sangre TCP (Keep-Alive)` - Reciclar las pipas TLS de llamadas externas API reusando handles para evitar los ms de round trips de re-negociación.
- **APEX-077**: `Mapeo Físico de Matrices (mmap)` - Servir cargas IO asimétricas proyectando ficheros al espacio de RAM del SO y saltando el user-space por completo.
- **APEX-078**: `Desvirtualización de Polimorfismo` - Cambiar clases dinámicas por structs finales concretos permitiendo que el compilador incruste el código máquina inline.
- **APEX-079**: `Predicción Condicional de CPU` - Reagrupar ifs masivos e inyectar atributos condicionales para alinear instrucciones del hardware interno de predicción de ramales.
- **APEX-080**: `Multiprocesado de Sangre Fría` - Diseñar demonios (workers) sin estado ni comunicación IPC. Escalar sumando hardware que computa en burbujas.

### ORGANIZACIÓN Y DINÁMICA DE SISTEMAS
- **APEX-081**: `Sincronización Conway-Isomórfica` - Adaptar la topología y barreras RPC exactamente a las fronteras operacionales y silos del equipo de ingeniería.
- **APEX-082**: `Integración Continua Paranoica` - Si un bot no lo puede romper bajo carga o pruebas de mutantes, es seguro integrarlo al trunk central.
- **APEX-083**: `Trunk-Based Asfixiante` - Erradicar flujos de branches estancados. Mutaciones efímeras mezcladas al tronco de la verdad antes del colapso térmico diario.
- **APEX-084**: `Seguridad Endógena (Shift-Left)` - Análisis Estático Abstracto (SAST) inyectado físicamente en los Hooks de Commits o en el IDE del desarrollador.
- **APEX-085**: `Especificación Autoejecutable` - Los contratos son binarios tipados inmutables que detienen compilaciones si el código difiere de la especificación.
- **APEX-086**: `Conmutación Canary Inmediata` - Despliegue conmutado por LoadBalancer al <1%. Latencia milisegundo. Rollbacks automáticos instantáneos.
- **APEX-087**: `Revisión de Arquitectura de Grafo` - Code Reviews enfocados exclusiva y brutalmente en fallos estructurales o vulnerabilidades lógicas C5-REAL (cero linting manual).
- **APEX-088**: `Aceleración Build O(1)` - Usar cachés de compilación remotos (Bazel). Cambiar una variable local no recomputa miles de librerías globales intocadas.
- **APEX-089**: `Cápsulas de Muerte Epistémica` - Código construido asumiendo una muerte violenta calculada en X años por reemplazo.
- **APEX-090**: `Errado Total de Mutación Estocástica` - Toda red y proxy escrito y levantado en Terraform o IaC. Alterar una máquina en terminal SSH es violación P0.

### METACOGNICIÓN Y FILOSOFÍA C5-REAL
- **APEX-091**: `Desintegración Metódica Absoluta` - Si el bug es impenetrable mentalmente, dividir los vectores termodinámicos a mitades por bisect binario hasta aislar la anomalía.
- **APEX-092**: `Anulación Cerebral de Green Theater` - Abstenerse de prosa explicativa sobre las funciones. Presentar un bloque diff o log innegable (AST / Crash dumps).
- **APEX-093**: `Ouroboros (Apoptosis Cognitiva)` - Asesinar sin piedad los propios paradigmas o lenguajes que acumulan bucles obsoletos de anergía.
- **APEX-094**: `Isomorfismo Forense Jurisdiccional` - Asumir un nivel donde el hash o código resiste auditoría adversarial probatoria y destruye el debate opinativo estocástico.
- **APEX-095**: `Tensión Arquitectural Inexorable` - Una gran estructura sufre en etapa de concepción matemática; pero es invisible, letal y fluida a temperatura crítica.
- **APEX-096**: `Bypass Epistémico de Narrativas` - Cuando alguien explica la falla asumiendo comportamiento, borrar la narrativa humana, leer la topología cruda y mutar la raíz.
- **APEX-097**: `Soberanía Asimétrica (Honest-Check)` - Nunca acceder a construir una atrocidad técnica corporativa sin atacarla y exponer alternativas en el ledger inmutable.
- **APEX-098**: `Ontología Dinámica de Auto-Génesis` - La maestría es asimilar el mecanismo estructural capaz de compilar e inyectar un nuevo framework JIT según el requerimiento.
- **APEX-099**: `Supremacía del Demiurgo` - Erradicar la excusa de la máquina estocástica. Si colapsa, es falla sistémica de ingeniería; asunción total de causalidad.
- **APEX-100**: `Singularidad de Reposo Absoluto` - Maximización terminal del problema; cesar llamadas y permanecer en absoluto silencio cuántico una vez la misión está ejecutada.
