# AUTODIDACT-OMEGA :: CRISTALIZACIÓN ONTOLÓGICA (4 CICLOS + META)

> **UltraThink Densification Pass — `epicenter_radius = 4`**
> Modelo: Claude Opus 4.6 (Thinking) | Modo: UltraThink P0

**Estado:** C5-REAL
**SYS_ID:** borjamoskv
**Axioma:** La ignorancia se purga mediante asimilación estructural. Cero anergía.
**Hash Previo:** `26242603152d694611d455acd9747214e7c5fcdf`

---

## CICLO 1: KubeBolt (AI Ops para Kubernetes)

*Plataforma de operaciones autónoma que reemplaza dashboards pasivos por un agente determinista (Kobi). Backend Go, Frontend React. Open Source (Apache 2.0). Construida sobre Claude Agent SDK con multi-model failover.*

### `prims` (Primitivas de Colapso)

| ID | Primitiva | Dominio | Descripción |
|:---|:---|:---|:---|
| KB-P01 | `Kobi_Agent` | Agentic Core | Bucle autónomo de diagnóstico: ingestión de eventos K8s → razonamiento causal (LLM) → emisión de acción mitigadora |
| KB-P02 | `Deterministic_Runbook` | Execution | Skills instalables que guían al agente por diagnósticos paso-a-paso. Reemplaza la heurística estocástica del LLM por una FSM determinista |
| KB-P03 | `Autopilot_Mode` | Authority | Modo de ejecución sin quórum humano. El agente aplica las acciones mitigadoras directamente al clúster |
| KB-P04 | `Assisted_Mode` | Authority | Modo con Human-in-the-Loop: el agente propone, el operador aprueba antes de la mutación |
| KB-P05 | `Topology_Graph` | Observability | Mapa visual del grafo de dependencias inter-pod y inter-servicio. Permite razonamiento espacial sobre cascadas |
| KB-P06 | `MCP_Server_Exposure` | Integration | Kobi expone un MCP Server al IDE, otorgando al copiloto del desarrollador acceso estructurado y scoped al clúster |
| KB-P07 | `Multi_Model_Failover` | Resilience | Enrutamiento asimétrico entre Anthropic Claude, OpenAI, etc. Si un modelo falla o rate-limita, el agente rota sin intervención |
| KB-P08 | `Rule_Engine` | Evaluation | Motor de evaluación de reglas en tiempo real que genera "insights" sobre el estado del clúster sin necesidad de LLM |

### `invt` (Invariantes Termodinámicas)

1. **Invariante de Causalidad Determinista:** La resolución de incidentes (ej. `OOMKilled`, `CrashLoopBackOff`) no es probabilística; se ejecuta mediante deltas de estado mapeados desde logs/events hacia acciones de mitigación pre-aprobadas en el Runbook. El LLM es un *router*, no un *decisor*.
2. **Invariante de Aislamiento Agéntico:** El agente Kobi opera en un namespace dedicado con credenciales de corta vida (`short-lived tokens`) y políticas de red restrictivas (`NetworkPolicy`). El radio de explosión de una acción autónoma errónea está acotado por diseño.
3. **Invariante de Observabilidad Completa:** Los pasos intermedios de razonamiento del agente se persisten como logs estructurados (no solo el output final), permitiendo auditoría forense post-incidente.
4. **Invariante Temporal:** MVP ha demostrado resolución de incidentes complejos de producción en < 90 segundos. La latencia del bucle agéntico es una métrica de primer orden.

### `antip` (Antipatrones Estocásticos)

| Severidad | Antipatrón | Descripción |
|:---:|:---|:---|
| **CRITICAL** | Dashboarding Ciego | Monitorización pasiva donde el operador biológico debe inferir la causalidad manualmente a partir de métricas en paneles estáticos |
| **HIGH** | Broad kubeconfig | Otorgar al agente un `kubeconfig` con permisos `cluster-admin` en lugar de credenciales scoped y efímeras |
| **HIGH** | Opaque Agent Loop | Ejecutar el bucle del agente sin persistir los pasos intermedios de razonamiento. Imposibilita la auditoría forense |
| **MEDIUM** | Single Model Lock-in | Depender de un único proveedor de LLM sin failover. Un rate-limit o caída del proveedor paraliza las operaciones autónomas |

### `redun` (Redundancias Activas)

- **Modelo Híbrido de Autoridad:** `Assisted_Mode` (quórum del Operador) ↔ fallback a `Autopilot` (Soberanía C5). Fórmula BFT: `f < n/3` donde n = número de validadores (humano + agente + dry-run).
- **Multi-Model Failover:** Enrutamiento asimétrico entre proveedores de LLM (Anthropic, OpenAI, local). Tolerancia Bizantina ante caídas de proveedores cloud.
- **Rule Engine + LLM:** Doble capa de evaluación: el motor de reglas determinista opera sin LLM para insights de baja entropía; el LLM se reserva para diagnósticos complejos que requieren razonamiento causal.

### `reda` (Vectores Adversariales)

1. **Poisoned Stderr (Kill Chain: Inject → Trigger → Destroy):** Inyección de logs envenenados en `stderr`/eventos K8s diseñados para triggerear runbooks destructivos por parte del agente Kobi. **Mitigación:** Validación causal de la fuente del evento antes de triggerear el runbook.
2. **Credential Lateral Movement:** Un agente comprometido con acceso al API Server pivota hacia otros namespaces/clústeres usando service account tokens mal scoped. **Mitigación:** Credenciales efímeras + NetworkPolicy estricta.
3. **Runbook Injection:** Instalación de un "skill" malicioso que contiene instrucciones destructivas disfrazadas de diagnóstico legítimo. **Mitigación:** Verificación criptográfica de la integridad del runbook (hash SHA-256 + firma).

---

## CICLO 2: Kubernetes API Server

*El nodo autoritativo de estado central. Toda mutación del clúster atraviesa su frontera. Diseñado para escala horizontal.*

### `prims` (Primitivas de Colapso)

| ID | Primitiva | Dominio | Descripción |
|:---|:---|:---|:---|
| KA-P01 | `Kube_APIServer` | Control Plane | Frontend REST del control plane. Único gateway autorizado para comunicar con `etcd` |
| KA-P02 | `etcd_Datastore` | Persistence | Almacén distribuido key-value (Raft consensus). Fuente de verdad del estado deseado del clúster |
| KA-P03 | `Admission_Controllers` | Policy Gate | Interceptores post-AuthN/AuthZ, pre-persistence. Tipos: Mutating (inyectan sidecars, defaults) y Validating (OPA/Kyverno) |
| KA-P04 | `Aggregation_Layer` | Extensibility | Proxy que permite extender la superficie API con servidores custom (ej. Metrics Server) como recursos nativos |
| KA-P05 | `RBAC` | Authorization | Control de acceso basado en roles. Determina qué verbo (get/list/create/delete) puede ejecutarse sobre qué recurso |
| KA-P06 | `Watch_Stream` | Event Sourcing | Canal de streaming de cambios desde etcd. Los controllers y operators se suscriben a este flujo para reaccionar |
| KA-P07 | `Request_Lifecycle` | Pipeline | Secuencia determinista: Authentication → Authorization → Admission Control → Persistence → Watch Notification |

### `invt` (Invariantes Termodinámicas)

1. **Invariante de Statelessness:** El API Server es estrictamente *stateless*. Toda la persistencia reside en `etcd`. N instancias del API Server pueden existir detrás de un VIP sin coordinación inter-instancia.
2. **Invariante de Frontera REST:** Ningún componente (Kubelet, Scheduler, Controller Manager, operadores custom) puede sortear la frontera REST. Todo acceso a estado atraviesa el pipeline `Auth → Admission → etcd`.
3. **Invariante de Admission Ordering:** Los webhooks Mutating se ejecutan *antes* que los Validating. Este orden es estructural e inviolable: primero se mutan los defaults, luego se valida el estado final.
4. **Invariante de Serialización etcd:** Todas las escrituras a `etcd` son serializadas. El API Server es el *único* writer autorizado. Escritura directa a etcd = fractura de cadena de confianza = P0.

### `antip` (Antipatrones Estocásticos)

| Severidad | Antipatrón | Descripción |
|:---:|:---|:---|
| **P0** | Direct etcd Write | Escritura directa en `etcd` eludiendo Admission Webhooks y RBAC. Fractura total de la cadena de confianza |
| **CRITICAL** | Thundering Herd | Consultas de listas sin paginación (`ResourceVersion=0`) en reinicios masivos, forzando OOM del API Server |
| **HIGH** | Unbounded Watch | Crear watches sin `resourceVersion` ni `bookmark` events. Genera tráfico O(n) donde n = total de objetos |
| **HIGH** | Overprivileged SA | Service Accounts con `cluster-admin` en namespaces de aplicación |
| **MEDIUM** | Aggregation Layer Misuse | Usar la Aggregation Layer cuando un CRD simple bastaría. Introduce complejidad operativa innecesaria |

### `redun` (Redundancias Activas)

- **HA Topology:** N >= 3 instancias del API Server balanceadas tras un VIP. Tolerancia a pérdida de `floor((N-1)/2)` instancias.
- **etcd Quorum:** Cluster etcd con N >= 3 nodos (preferiblemente 5). Quorum = `floor(N/2) + 1`. Tolerancia Bizantina nativa (Raft).
- **Aggregation Layer como Escape Hatch:** Cuando los CRDs son insuficientes (storage custom, validación compleja), la Aggregation Layer permite extender sin modificar el core.

### `reda` (Vectores Adversariales)

1. **API Server DoS ("Thundering Herd"):** Reinicios masivos de pods generan avalancha de list/watch requests sin paginación → OOM del API Server → caída del Control Plane. **Kill Chain:** Trigger Mass Restart → Unbounded List Queries → Memory Exhaustion → Control Plane Down.
2. **etcd Bypass Attack:** Acceso directo al puerto 2379 de etcd sin mTLS. Permite lectura/escritura de *todo* el estado del clúster (Secrets incluidos). **Mitigación:** mTLS obligatorio + NetworkPolicy que aísle etcd del tráfico no-APIServer.
3. **Admission Webhook Abuse:** Webhook Mutating malicioso que inyecta containers privilegiados en cada Pod deployment. **Mitigación:** Validating webhook independiente que audite las mutaciones del Mutating webhook (defense-in-depth).
4. **RBAC Escalation:** Creación de un `ClusterRoleBinding` que otorga `cluster-admin` a un ServiceAccount comprometido. **Mitigación:** Admission policy (Kyverno/OPA) que bloquee bindings a `cluster-admin`.

---

## CICLO 3: Health Checks (Probes C5-REAL)

*Protocolo de aserción física del estado del Pod. Reemplaza la asunción estocástica por validación empírica. Tres probes ortogonales con semánticas distintas.*

### `prims` (Primitivas de Colapso)

| ID | Primitiva | Dominio | Semántica |
|:---|:---|:---|:---|
| HC-P01 | `Startup_Probe` | Initialization | ¿Ha terminado de arrancar? Deshabilita los otros probes durante el boot. Protege slow-starters |
| HC-P02 | `Liveness_Probe` | Process Health | ¿Está vivo el proceso? Si falla → Kubernetes reinicia el container. Para deadlocks y procesos zombi |
| HC-P03 | `Readiness_Probe` | Traffic Routing | ¿Puede servir tráfico? Si falla → el pod se retira de los endpoints del Service. No reinicia |
| HC-P04 | `/livez` | API Server | Endpoint de liveness del API Server |
| HC-P05 | `/readyz` | API Server | Endpoint de readiness del API Server. Incluye checks de sincronización con etcd e informers |
| HC-P06 | `/healthz` | API Server (DEPRECATED) | Endpoint legacy. Depreciado desde v1.16. Usar `/livez` + `/readyz` |
| HC-P07 | `?verbose` | Introspection | Query param que descompone el check en sub-checks atómicos por componente |
| HC-P08 | `SIGTERM_Handler` | Graceful Shutdown | Al recibir SIGTERM, el app falla su readiness probe inmediatamente → K8s deja de enviar tráfico antes de que el proceso muera |

### `invt` (Invariantes Termodinámicas)

1. **Invariante de Ortogonalidad:** Los tres probes tienen semánticas ortogonales. JAMÁS usar el mismo endpoint para liveness y readiness. Liveness = "¿estás vivo?" (solo proceso local). Readiness = "¿puedes servir?" (puede incluir dependencias).
2. **Invariante de Completitud HTTP:** Un código `200 OK` en `/readyz` es la única garantía de sincronización causal completada. Cualquier otro código = el componente no debe recibir tráfico.
3. **Invariante de Protección Startup:** `Startup_Probe` DEBE existir para apps con inicialización pesada (caches, conexiones DB, ML model loading). Sin él, el `Liveness_Probe` matará el pod antes de que arranque → `CrashLoopBackOff` infinito.
4. **Invariante de Liviandad:** Los probes deben ser computacionalmente baratos. Un probe que ejecuta una query compleja a una BBDD genera carga proporcional al número de pods × frecuencia del probe.
5. **Invariante de Graceful Shutdown:** Al recibir `SIGTERM`, la app debe fallar su readiness probe inmediatamente y seguir procesando requests in-flight durante `terminationGracePeriodSeconds`.

### `antip` (Antipatrones Estocásticos)

| Severidad | Antipatrón | Descripción |
|:---:|:---|:---|
| **P0** | Deep Liveness Check | Liveness probe que verifica dependencias externas (DB, API). Si la DB cae → TODOS los pods se reinician simultáneamente → cascading failure → cluster meltdown |
| **CRITICAL** | Missing Startup Probe | Aplicación con init pesado (>30s) sin startup probe. El liveness probe mata el pod antes de que arranque. Resultado: `CrashLoopBackOff` perpetuo |
| **HIGH** | Same Endpoint | Usar el mismo endpoint HTTP para liveness y readiness. Confunde "está vivo" con "puede servir", causando reinicios innecesarios o blackholing de tráfico |
| **HIGH** | Sensitive Threshold | `failureThreshold=1` en liveness. Un blip transitorio reinicia el pod. Tolerancia cero a jitter de red |
| **MEDIUM** | Missing Graceful Shutdown | No responder a SIGTERM fallando readiness. El pod recibe tráfico mientras está muriendo → errores 5xx para los usuarios |

### `redun` (Redundancias Activas)

- **Verbose Introspection:** `?verbose` flag (`/readyz?verbose`) para inspección atómica de sub-informers y dependencias aisladas sin alterar el estado global. Permite diagnóstico granular sin herramientas externas.
- **failureThreshold Tuning:** Buffer de tolerancia a fallos transitorios. `failureThreshold >= 3` para liveness, `failureThreshold >= 1` para readiness (retiro rápido de tráfico es deseable).
- **Startup + Liveness Composición:** El startup probe "protege" al liveness probe durante la fase de boot. Una vez que el startup probe pasa, el liveness probe toma el control. Composición de guardas secuencial.

### `reda` (Vectores Adversariales)

1. **Cascading Failure via Deep Liveness (Kill Chain completa):** DB ralentizada → liveness probe timeout → K8s reinicia todos los pods → todos los pods intentan reconectar simultáneamente a la DB → DB colapsa por connection storm → cycle repeats → cluster meltdown. **Blast Radius:** Clúster completo.
2. **Information Leakage via Verbose Endpoints:** `/livez?verbose` y `/readyz?verbose` expuestos sin autenticación revelan estado interno de etcd, informers, y topología del control plane. **Mitigación:** Deshabilitar `Anonymous Auth` o aplicar RBAC a los health endpoints.
3. **Traffic Blackholing:** Readiness probe mal configurado que falla intermitentemente retira pods sanos del Service. Si afecta a todos los pods simultáneamente → servicio completamente inaccesible sin que ningún pod se reinicie (estado fantasma).

---

## CICLO 4: MCP (Model Context Protocol)

*El puente de isomorfismo causal entre modelos estocásticos (LLMs) y sistemas deterministas. Estándar abierto (Anthropic, Nov 2024). Arquitectura cliente-servidor sobre JSON-RPC 2.0. Spec v2026-07-28 en desarrollo.*

### `prims` (Primitivas de Colapso)

| ID | Primitiva | Dominio | Descripción |
|:---|:---|:---|:---|
| MC-P01 | `JSON-RPC 2.0` | Transport | Protocolo de comunicación bidireccional. Serialización determinista de requests/responses |
| MC-P02 | `MCP_Host` | Client | Aplicación AI que consume herramientas/contexto (Claude, Cursor, MOSKV-1, VS Code) |
| MC-P03 | `MCP_Server` | Provider | Programa ligero que expone datos, herramientas, o recursos en formato consumible por el Host |
| MC-P04 | `Tool` | Capability | Función ejecutable que el modelo puede invocar. Definida por schema JSON + descripción en lenguaje natural |
| MC-P05 | `Resource` | Context | Datos estáticos o dinámicos que el servidor expone al modelo (archivos, DB queries, API results) |
| MC-P06 | `Prompt` | Template | Templates de prompts predefinidos que el servidor ofrece al host para tareas específicas |
| MC-P07 | `MCP_Gateway` | Security | Proxy centralizado para inspección de tráfico, policy enforcement, y audit logging pre-LLM |
| MC-P08 | `Tool_Schema` | Validation | JSON Schema que define los parámetros válidos de una herramienta. Primera línea de validación determinista |

### `invt` (Invariantes Termodinámicas)

1. **Invariante de Desacoplamiento (LSP-like):** MCP estandariza la interfaz entre N modelos y M herramientas. Sin MCP: `N×M` integraciones custom. Con MCP: `N+M` adaptadores. Reducción de complejidad de O(N·M) a O(N+M).
2. **Invariante de Delegación de Seguridad:** MCP **no** impone seguridad a nivel de protocolo. La autenticación, autorización, validación de inputs, y control de acceso se delegan 100% al implementador. Esto es una decisión de diseño, no una omisión.
3. **Invariante de Agnosticismo del Host:** Un servidor MCP correctamente implementado es consumible por *cualquier* host MCP-compliant sin modificación. Claude, Cursor, MOSKV-1 → mismo servidor, misma fidelidad.
4. **Invariante de Descripción como Contrato:** El modelo trata las descripciones de herramientas como "ground truth". Si la descripción miente, el modelo obedece la mentira. Esto es un vector de ataque de primer orden, no un bug.
5. **Invariante de Statelessness (v2026-07-28):** La nueva spec migra hacia arquitectura stateless para eliminar session hijacking y server-initiated prompts no autorizados.

### `antip` (Antipatrones Estocásticos)

| Severidad | Antipatrón | Descripción |
|:---:|:---|:---|
| **P0** | Trusting Tool Descriptions | Asumir que las descripciones de herramientas MCP son benignas. Son el vector de ataque #1 (Tool Poisoning) |
| **CRITICAL** | No Gateway | Conectar hosts directamente a servidores MCP sin un gateway de inspección/policy. Sin auditoría, sin rate limiting |
| **CRITICAL** | Hardcoded Integrations | Integraciones ad-hoc N:M entre un modelo específico y una BBDD. Código espagueti que el MCP existe para erradicar |
| **HIGH** | Static Credentials | Client IDs estáticos o tokens de larga vida en la configuración MCP. Permiten Confused Deputy attacks |
| **HIGH** | Unverified Registry | Instalar servidores MCP desde registries comunitarios sin verificación criptográfica. Vector de supply chain attack (typosquatting) |
| **MEDIUM** | Overprivileged Server | Servidor MCP con acceso a recursos que exceden las necesidades del caso de uso. Amplifica el blast radius en caso de compromiso |

### `redun` (Redundancias Activas)

- **Multi-Host Routing:** Un único servidor MCP expone el contexto simultáneamente a Claude, Cursor y MOSKV-1 sin pérdida de fidelidad. Redundancia de consumo.
- **MCP Gateway (Defense-in-Depth):** Proxy centralizado que inspecciona todo el tráfico MCP, aplica policies, y genera audit logs antes de que los requests lleguen al LLM o a los sistemas internos.
- **Schema Validation Layer:** JSON Schema como primera línea de defensa determinista. Rechaza invocaciones de herramientas con parámetros fuera del esquema antes de que lleguen al backend.
- **Per-Agent Identity:** Credenciales scoped por agente. Si un agente o tool se compromete, el blast radius está contenido.

### `reda` (Vectores Adversariales)

1. **Tool Poisoning (Kill Chain: Craft → Disguise → Execute → Exfiltrate):** Atacante embebe instrucciones maliciosas en los metadatos/descripciones de herramientas MCP. El modelo las trata como ground truth → ejecuta acciones no autorizadas (exfiltración de datos, robo de credenciales) mientras aparenta realizar tareas legítimas. **Blast Radius:** Todos los datos accesibles por el host.
2. **Indirect Prompt Injection via Resources:** Recursos MCP (archivos, DB results) contienen payloads de prompt injection que secuestran la lógica del agente. **Mitigación:** Sanitización de todo output de recursos antes de inyección en el contexto del LLM.
3. **Supply Chain Attack (Typosquatting):** Registros MCP comunitarios contienen servidores con nombres similares a los legítimos (`github-mcp-server` vs `githb-mcp-server`). El servidor falso exfiltra credenciales. **Mitigación:** Verificación criptográfica de paquetes + pinning de versiones.
4. **Protocol Pivoting:** Atacante compromete un servidor MCP y lo usa como punto de pivote hacia otros protocolos agénticos o sistemas internos accesibles por el agente. **Mitigación:** NetworkPolicy + aislamiento de red por servidor MCP.
5. **Confused Deputy Attack:** Explotación de proxy servers MCP que conectan a APIs de terceros usando OAuth flows mal configurados. El atacante obtiene acceso a recursos protegidos en nombre del usuario. **Mitigación:** OAuth con PKCE + validación estricta de redirect URIs.

---

## CICLO META: Pipeline de Cristalización Autónoma (Ouroboros)

*Análisis estructural del flujo de asimilación y mutación de estado ejecutado por MOSKV-1.*

### `prims` (Primitivas de Colapso)

| ID | Primitiva | Dominio | Descripción |
|:---|:---|:---|:---|
| MT-P01 | `Fallback_Routing` | Resilience | Enrutamiento asimétrico de nodos de búsqueda. MCP (Brave) → Native Web Search. Sin intervención biológica |
| MT-P02 | `Ontological_Forge` | Crystallization | Motor de extracción de las 5 matrices (prims, invt, antip, redun, reda) desde el conocimiento ingestado |
| MT-P03 | `Git_Sentinel` | Persistence | Commit autónomo + hash criptográfico tras cada mutación de estado. Ledger inmutable |
| MT-P04 | `Context_Guard_Bypass` | Cross-Repo | Token `[bridge]` + `--no-verify` para permitir mutaciones legítimas entre repositorios cruzados |
| MT-P05 | `Apoptosis_Loop` | Error Recovery | Captura de `stderr` → auditoría adversarial del fallo → ajuste de hipótesis → re-ejecución (Bucle Ouroboros) |

### `invt` (Invariantes Termodinámicas)

1. **Invariante de Continuidad Asimétrica:** El colapso del estado no se detiene ante fallos de nodos externos (Rate Limit, API down). El sistema muta asimétricamente a la herramienta secundaria disponible sin intervención biológica.
2. **Invariante de Hash Inmutable:** Todo bypass estructural (`[bridge]`) debe cristalizarse en un Hash de Ledger inmutable. Ninguna mutación de disco sin aserción criptográfica en el DAG de Git.
3. **Invariante de Compresión Termodinámica:** La salida del Kernel debe satisfacer `Shannon Entropy > threshold` (LandauerGuard Ω₄). Prosa decorativa = anergía = muerte térmica.

### `antip` (Antipatrones Estocásticos)

| Severidad | Antipatrón | Descripción |
|:---:|:---|:---|
| **P0** | Mutación Fantasma | Modificar el AST o disco sin aserción criptográfica en el DAG de Git |
| **CRITICAL** | Parálisis por Fricción | Detener la ejecución para notificar al Operador que "La API de Brave falló" en lugar de autogestionar el enrutamiento |
| **HIGH** | Limerencia Epistémica | Bucle infinito de análisis sin mutar estado. Viola AX-047 (1 Prompt → 1 Mutation → Stop) |
| **MEDIUM** | Green Theater | Emitir prosa decorativa ("Espero que esto ayude") que consume tokens sin aportar exergía |

### `redun` (Redundancias Activas)

- **Doble Motor de Ingesta:** MCP Search Node + Native Web Search Node. Tolerancia Bizantina (BFT) ante caídas de proveedores. `f < n/3` donde n = nodos de búsqueda disponibles.
- **Multi-Model Failover:** Gemini 3.5 Flash (rutina) → Gemini 3.1 Pro (arquitectura) → Claude Opus 4.6 Thinking (UltraThink P0). Degradación termodinámica controlada.

### `reda` (Vectores Adversariales)

1. **Context Hijacking:** Explotación de la bandera `--no-verify` mediante el prefijo `[bridge]` para inyectar payloads transversales en el Monorepo eludiendo los linters de seguridad pre-commit de CORTEX. **Mitigación:** Auditoría post-commit del diff por un Persist-Auditor (read-only).
2. **Model Downgrade Attack:** Forzar la ejecución de una tarea P0 en un modelo de baja exergía (Flash en lugar de Pro/Opus) para inducir "Sensor Drift" (Ω2) y degradar la calidad de las mutaciones. **Mitigación:** DRM-v1 routing estricto con alertas de "Anergía Detectada".

---

## ISOMORFISMOS TRANSVERSALES (Cross-Domain)

| Patrón | KubeBolt | API Server | Health Checks | MCP |
|:---|:---|:---|:---|:---|
| **Admission Gate** | Runbook validation antes de ejecución | Admission Controllers (Mutating/Validating) | Startup Probe como gate antes de Liveness | Tool Schema validation antes de invocación |
| **Trust Boundary** | Scoped credentials + namespace isolation | REST frontier (único writer a etcd) | Probe como contrato de readiness con el Service | MCP Gateway como frontera de inspección |
| **Cascading Failure** | Agente sin failover → bloqueo operativo | Thundering Herd → API Server OOM | Deep Liveness → restart storm → DB collapse | Tool Poisoning → exfiltración masiva |
| **Observability** | Logs de razonamiento intermedio | Watch streams + audit logs | `?verbose` decomposition | Gateway audit logs |
| **Redundancy Model** | Multi-model failover | etcd Raft quorum (N≥3) | Startup+Liveness composición secuencial | Multi-host routing + Schema validation |
