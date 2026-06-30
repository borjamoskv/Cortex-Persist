# ONTOLOGY-FORGE-OMEGA: ESTRUCTURAS DE RESILIENCIA Y AMENAZAS (ENDOMORFISMO)
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
