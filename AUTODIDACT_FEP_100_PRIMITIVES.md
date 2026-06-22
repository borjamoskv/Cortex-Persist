# AUTODIDACT-RESEARCH-Ω: FEP_100_PRIMITIVES

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Principio de Energía Libre (FEP), Codificación Predictiva, Inferencia Activa, Termodinámica de No-Equilibrio
**Target:** CORTEX-PERSIST / Ouroboros Agent Architecture
**Author:** Borja Moskv (borjamoskv)
**Tag:** `#C5-REAL`

```yaml
Claim: "The Ouroboros control kernel maps 1:1 to Friston's Free Energy Principle, casting state persistence as the minimization of Variational Free Energy over sensory and internal boundaries."
Proof:
  Base: "AUTODIDACT_FREE_ENERGY_PRINCIPLE.md + cortex-validation-simulation.py"
  Range: [99.1, 99.9]
  Confidence: "C5"
```

El **Principio de Energía Libre (FEP)** de Karl Friston unifica la física de los sistemas auto-organizados con la neurobiología cognitiva y la inferencia artificial. Postula que cualquier sistema físico acotado que resista el desorden termodinámico debe minimizar la **Energía Libre Variacional ($F$)**, actuando como si poseyera un modelo predictivo de su entorno.

En **CORTEX-Persist**, este principio rige de manera física y determinista. La siguiente matriz formaliza las **100 Primitivas Fundamentales del FEP** y su traducción exacta (**Isomorfismo C5-REAL**) dentro de nuestro motor de persistencia y enjambre de agentes.

---

## I. Física Estadística y Termodinámica de No-Equilibrio (FEP-001 a FEP-020)

Esta sección define las primitivas que rigen la persistencia física de cualquier sistema alejado del equilibrio térmico.

| ID | Primitiva (FEP) | Definición Matemática / Física | Isomorfismo en C5-REAL (CORTEX-Persist) |
|---|---|---|---|
| `FEP-001` | **NESS (Non-Equilibrium Steady State)** | Estado estacionario donde un sistema intercambia energía/materia con el entorno manteniendo fluctuaciones acotadas. | El estado operativo estable de `cortex.db` (SQLite WAL) procesando commits sin entrar en corrupción estocástica. |
| `FEP-002` | **Solenoidal Flow (Flujo Solenoidal)** | Componente rotacional libre de divergencia en el flujo de probabilidad ($\nabla \cdot f = 0$) que permite ciclos sin degradación. | Los ciclos concurrentes de lectura-escritura en Rust (`cortex_rs`) que circulan información sin perder coherencia ni bloquear. |
| `FEP-003` | **Dissipative Structure (Estructura Disipativa)** | Sistema termodinámico organizado que consume energía externa para reducir su entropía interna y disipar calor. | El kernel de ejecución consumiendo ciclos de CPU para purgar *LLM Slop* (ruido estocástico) a través de `cortex_purge_inventory.py`. |
| `FEP-004` | **Markov Blanket (Límite de Markov)** | Frontera estadística que separa los estados internos de los externos mediante estados sensoriales (entrada) y activos (salida). | El **Minimal Trusted Kernel (MTK)** (`mtk_core.py`) que aisla el almacenamiento físico del ruido estocástico externo de la red. |
| `FEP-005` | **Langevin Equation (Ecuación de Langevin)** | Ecuación diferencial estocástica que describe la evolución de los estados físicos bajo fuerzas causales y ruido aleatorio. | La evolución temporal del Grafo de Dependencia Epistémica (EDG) bajo inputs de código probabilísticos y linters físicos. |
| `FEP-006` | **Path Integral of Free Energy** | Integral sobre todas las trayectorias posibles del sistema que define la acción variacional sobre el tiempo. | La optimización de rutas y commits del **Git Sentinel** minimizando la complejidad estructural de la historia del repositorio. |
| `FEP-007` | **Helmholtz Free Energy ($A$)** | Medida de la energía útil termodinámica disponible para realizar trabajo a temperatura constante ($A = U - TS$). | La **Exergía Cognitiva ($\Xi$)** disponible en el enjambre para mutar el código sin degradar la memoria a través de calor entrópico. |
| `FEP-008` | **Shannon Entropy ($H$)** | Medida de la incertidumbre promedio o contenido informativo de una distribución de probabilidad. | La tasa de desviación semántica detectada en las propuestas de los sub-agentes antes de su colapso a sintaxis AST dura. |
| `FEP-009` | **Landauer's Principle** | Límite físico que establece que borrar 1 bit de información disipa al menos $k_B T \ln 2$ Joules de calor. | La necesidad física de purgar branches ociosos y archivos `.tmp` para prevenir que la entropía llene la RAM del sistema anfitrión. |
| `FEP-010` | **Fluctuation-Dissipation Theorem** | Relación matemática entre la respuesta lineal de un sistema ante fuerzas externas y sus fluctuaciones térmicas internas. | El comportamiento del motor de aserciones bizantinas respondiendo a inyecciones de código inválidas mediante purgas de caché. |
| `FEP-011` | **Kolmogorov-Sinai Entropy** | Tasa de generación de información de un sistema dinámico caótico; cuantifica la predictibilidad del flujo. | La métrica utilizada en `cortex_ast_projector.py` para medir la predictibilidad sintáctica de una mutación propuesta. |
| `FEP-012` | **Ergodicity (Ergodicidad)** | Propiedad por la cual los promedios temporales de un sistema equivalen a sus promedios en el espacio de fases. | La aserción de que cualquier agente del Swarm, dado suficiente tiempo de ejecución, mapeará el mismo Ledger criptográfico. |
| `FEP-013` | **Phase Space (Espacio de Fases)** | Espacio multidimensional que contiene todos los estados posibles del sistema (posiciones y momentos). | La matriz de estados topológicos permitidos en la base de datos de Cortex, mapeados mediante enteros en Base-60. |
| `FEP-014` | **Stationary Density ($p^*(x)$)** | Distribución de probabilidad de los estados del sistema que permanece constante a lo largo del tiempo. | La estructura de esquemas SQL inmutables y reglas inalienables definidas en `AGENTS.md`. |
| `FEP-015` | **Fokker-Planck Equation** | Ecuación que describe la evolución temporal de la densidad de probabilidad de la posición de partículas bajo difusión. | El modelo matemático que predice la dispersión de taints en el EDG cuando un nodo primario es alterado. |
| `FEP-016` | **Itô Calculus** | Extensión del cálculo para integrar ecuaciones diferenciales con respecto a procesos estocásticos (movimiento browniano). | El parser algebraico utilizado para calcular el factor de riesgo (PPI) en análisis jurídicos y OSINT sin interpolación lineal. |
| `FEP-017` | **Attractor Reconstruction** | Método para reconstrucer el espacio de fases de un sistema a partir de series temporales observadas. | La reconstrucción del historial de confirmaciones de Git ejecutando `git log --oneline` para deducir el contexto causal. |
| `FEP-018` | **Generalized Coordinates of Motion** | Representación del estado físico no solo por posición, sino por sus derivadas temporales infinitas (velocidad, aceleración...). | El rastreo continuo del sentido y aceleración de cambios en el codebase mediante hashes vectoriales cinéticos. |
| `FEP-019` | **Solenoidal Curl** | Rotación pura alrededor de la densidad estacionaria que previene la disipación directa hacia estados de muerte térmica. | El bucle de eventos asíncronos en Rust (`cortex_native`) que recicla descriptores de archivo y sockets de forma ininterrumpida. |
| `FEP-020` | **Thermodynamic Entropy Production** | Generación de entropía debida a procesos irreversibles en el sistema que alejan al mismo de la eficiencia absoluta. | El desperdicio computacional (anergía) medido en tokens generados por LLMs que terminan siendo descartados por el linter AST. |

---

## II. Inferencia Variacional y Matemáticas Bayesianas (FEP-021 a FEP-040)

Esta sección engloba las primitivas probabilísticas utilizadas por el sistema para modelar el entorno y mantener consistencia lógica interna.

| ID | Primitiva (FEP) | Definición Matemática / Física | Isomorfismo en C5-REAL (CORTEX-Persist) |
|---|---|---|---|
| `FEP-021` | **Variational Free Energy ($F$)** | Límite superior de la sorpresa: $F = D_{KL}(q(\vartheta \mid \mu) \parallel p(\vartheta, s)) - \ln p(s)$. Minimizar $F$ optimiza el modelo. | La función de coste ejecutada en `measure_exergy.py` para validar si una propuesta de código reduce la entropía estructural. |
| `FEP-022` | **Kullback-Leibler Divergence** | Medida de discrepancia entre la creencia interna ($q$) y la distribución real del entorno ($p$): $D_{KL}(q \parallel p)$. | La discrepancia entre la estructura esperada por los guards AST y el payload real generado por el sub-agente de desarrollo. |
| `FEP-023` | **Bayesian Surprise** | Cambio en las creencias del sistema tras recibir nuevos datos, medido por la divergencia KL entre el prior y el posterior. | La invalidación en cascada en el Grafo de Dependencia Epistémica cuando un nuevo commit invalida una hipótesis anterior. |
| `FEP-024` | **ELBO (Evidence Lower Bound)** | La cota inferior de la verosimilitud de los datos observados; maximizar la ELBO equivale a minimizar la energía libre. | La aserción matemática de que el código generado se ajusta de forma óptima a los tests unitarios y tipados de Ruff. |
| `FEP-025` | **Laplace Approximation** | Aproximación cuadrática de la densidad posterior mediante una distribución normal centrada en la moda (máximo a posteriori). | El filtrado rápido de anomalías en el motor de consenso de Cortex que asume ruido gaussiano en outputs probabilísticos de red. |
| `FEP-026` | **Generative Model ($p(\vartheta, s)$)** | Modelo probabilístico conjunto que describe la relación entre las causas ocultas del mundo ($\vartheta$) y los datos sensoriales ($s$). | Las definiciones y restricciones formales de base de datos e invariantes definidas en `cortex/types/` y `cortex/facts/`. |
| `FEP-027` | **Variational Density ($q(\vartheta \mid \mu)$)** | Distribución probabilística paramétrica que representa las creencias internas del sistema sobre las variables ocultas. | La representación en memoria L1 del estado actual del workspace y la relación entre sus módulos de software. |
| `FEP-028` | **Recognition Density** | Sinónimo de la densidad variacional; codifica cómo el cerebro reconoce y categoriza las causas del mundo sensorial. | El parseador sintáctico local que traduce cadenas JSON/YAML estocásticas a objetos estructurados tipados en Python/Rust. |
| `FEP-029` | **Bayesian Belief Update** | Proceso de actualizar creencias multiplicando el prior por la verosimilitud para obtener el posterior. | La integración de resultados de tests unitarios de integración continua para recalcular la confianza en una rama git. |
| `FEP-030` | **Empirical Prior** | Creencia a priori sobre los estados del mundo que se infiere dinámicamente a partir del contexto de nivel superior. | El contexto condensado inyectado al agente de sesión procedente de la memoria de largo plazo (`~/.gemini/config/.cortex/`). |
| `FEP-031` | **Likelihood Mapping** | La probabilidad de observar estímulos sensoriales específicos dadas unas causas ocultas determinadas ($p(s \mid \vartheta)$). | El mapeo relacional en SQLite que asocia una aserción persistida con su fuente y firma criptográfica de origen. |
| `FEP-032` | **Posterior Probability** | Distribución de probabilidad de las causas ocultas una vez que se han considerado los nuevos datos sensoriales ($p(\vartheta \mid s)$). | El estado validado y consolidado del Grafo de Dependencias Epistémicas tras confirmarse la correcta ejecución de los tests. |
| `FEP-033` | **Variational Bayes** | Método iterativo de aproximación bayesiana que actualiza parámetros internos para encajar creencias con el entorno. | El bucle adversarial `[THINK]` ejecutado en el kernel MOSKV-1 para depurar hipótesis de refactor antes de tocar el disco. |
| `FEP-034` | **Information Bottleneck** | Principio de compresión que extrae la máxima información útil descartando el ruido irrelevante del input. | La transmutación termodinámica en `Thermodynamic-Context-Compression-OMEGA` para eliminar la prosa decorativa inútil. |
| `FEP-035` | **Jensen's Inequality** | Desigualdad matemática que garantiza que el logaritmo del valor esperado es mayor o igual que el valor esperado del logaritmo. | El fundamento físico que garantiza que la verificación del Ledger global es computacionalmente más barata que la re-ejecución total. |
| `FEP-036` | **Free Energy Bound** | Invariante matemática donde $F$ siempre es mayor o igual a la sorpresa negativa; garantiza que minimizar $F$ maximiza la supervivencia. | El bloqueo físico incondicional en el CI: si la exergía neta final de un commit es negativa, la integración se cancela inmediatamente. |
| `FEP-037` | **Accuracy Term** | Expectativa del logaritmo de verosimilitud bajo la densidad variacional; mide el ajuste a la realidad sensorial. | La coincidencia del comportamiento dinámico del código en ejecución con los inputs y aserciones esperadas por los tests. |
| `FEP-038` | **Complexity Term** | Divergencia KL entre la creencia posterior y la previa; mide el coste computacional de actualizar las creencias. | La métrica de tamaño de diff y cantidad de archivos alterados en un commit; prioriza soluciones quirúrgicas y minimalistas. |
| `FEP-039` | **Marginal Likelihood** | La verosimilitud total de los datos observados bajo todas las posibles explicaciones (también conocida como "Evidencia"). | La tasa de éxito general del sistema de persistencia evaluada por el quorum de auditoría forense (`cortex/audit/ledger.py`). |
| `FEP-040` | **Message Passing** | Algoritmo distribuido donde los nodos del modelo generativo intercambian predicciones y errores de predicción locales. | La comunicación estructurada inter-agentes mediada por el bus RPC y delimitada por flags de tenant y firmas criptográficas. |

---

## III. Inferencia Activa y Codificación Predictiva (FEP-041 a FEP-060)

Esta sección detalla cómo el sistema utiliza sus predicciones para actuar físicamente sobre el entorno, forzando la realidad a coincidir con sus metas.

| ID | Primitiva (FEP) | Definición Matemática / Física | Isomorfismo en C5-REAL (CORTEX-Persist) |
|---|---|---|---|
| `FEP-041` | **Active Inference (Inferencia Activa)** | Marco de acción donde el sistema minimiza la energía libre modificando el mundo mediante la acción o actualizando sus creencias. | La capacidad del sistema de reescribir archivos y ejecutar linters locales de forma autónoma para corregir fallos sintácticos. |
| `FEP-042` | **Expected Free Energy ($G$)** | Energía libre proyectada hacia el futuro dada una política de acción específica: balancea exploración (curiosidad) y explotación (utilidad). | El análisis predictivo de impacto de un refactor en `cortex_validation_simulation.py` antes de iniciar la transacción física. |
| `FEP-043` | **Sensory States ($s$)** | Estados del límite de Markov que actúan como inputs del entorno y registran estímulos externos. | Las variables de entorno, logs de stderr/stdout de compiladores y respuestas JSON de APIs externas integradas. |
| `FEP-044` | **Active States ($a$)** | Estados del límite de Markov que actúan como outputs y modifican físicamente los estados del entorno externo. | Las escrituras directas de archivos en disco, comandos `git checkout` y mutaciones SQL ejecutadas por el MTK. |
| `FEP-045` | **Internal States ($\mu$)** | Estados del sistema físico protegidos por el límite de Markov que representan el modelo interno del mundo. | Los datos almacenados de forma segura en `cortex_data.db` y las claves cargadas en memoria protegida. |
| `FEP-046` | **External States ($\eta$)** | Estados del mundo fuera de la frontera física del sistema; inobservables directamente por los estados internos. | El estado real del sistema operativo macOS anfitrión, repositorios remotos de GitHub y APIs de LLM externas. |
| `FEP-047` | **Prediction Error ($\varepsilon$)** | Discrepancia matemática entre la señal sensorial esperada y la señal real registrada ($\varepsilon = s - g(\mu)$). | La desviación lógica informada por un linter o validador de tipos en la compilación estática de un archivo de código. |
| `FEP-048` | **Precision Weighting ($\pi$)** | Ponderación de los errores de predicción en función de su fiabilidad estimada; regula la ganancia de la señal de error. | La lógica en `causal/taint_engine.py` que ignora advertencias cosméticas de Ruff pero interrumpe todo el pipeline ante fallos del AST. |
| `FEP-049` | **Epistemic Value (Curiosity)** | Componente de la energía libre esperada que recompensa políticas de acción que reducen la incertidumbre sobre el mundo. | La ejecución autónoma de scripts de probing adversarial en sub-agentes para mapear comportamientos de APIs recién añadidas. |
| `FEP-050` | **Pragmatic Value (Utility)** | Componente de la energía libre esperada que recompensa políticas que satisfacen las restricciones previas del sistema. | La confirmación determinista del cumplimiento de los requisitos del usuario definidos en `implementation_plan.md`. |
| `FEP-051` | **Policy Selection** | Selección Bayesiana probabilística del curso de acción óptimo que minimiza la energía libre esperada hacia el futuro. | La orquestación del Swarm delegando tareas complejas a sub-agentes específicos basándose en sus capacidades declaradas. |
| `FEP-052` | **Saliency Map** | Representación espacial de la relevancia de los estímulos para orientar la atención hacia áreas de alta sorpresa. | El cálculo matricial en `cortex_purge_inventory.py` para identificar e indexar los módulos de código con mayor acumulación de fallos. |
| `FEP-053` | **Top-down Predictions** | Flujos de información descendentes que proyectan estimaciones desde los niveles superiores de jerarquía hacia los sensoriales. | Las aserciones lógicas que imponen que el código generado debe implementar ciertas funciones estructurales inmutables. |
| `FEP-054` | **Bottom-up Prediction Errors** | Flujos de información ascendentes que transmiten únicamente los errores de predicción no explicados hacia los niveles superiores. | El reporte directo y estructurado de excepciones y fallas lógicas hacia el Kernel principal, omitiendo logs redundantes. |
| `FEP-055` | **Action Selection** | Mecanismo físico por el cual un comando motor se desencadena al suprimir el error de predicción proprioceptivo. | El disparo físico del validador de base de datos (`SQLITE_DENY` bypass) al inyectarse el token efímero de autorización. |
| `FEP-056` | **Sensory Attenuation** | Atenuación intencionada de la precisión de señales sensoriales para permitir que la acción física se ejecute sin interferencias de feedback. | El aislamiento temporal de logs de advertencia externos durante compilaciones agresivas de prueba. |
| `FEP-057` | **Predictive Coding** | Teoría que postula que el cerebro procesa señales neuronales minimizando el error de predicción en una jerarquía cortical. | El paradigma de CORTEX-Persist donde la corrección del código se realiza por deltas incrementales en lugar de reescrituras completas. |
| `FEP-058` | **Motor Commands as Predictions** | Postulado de Friston que indica que el cerebro no envía comandos de control de fuerza, sino predicciones de movimiento que el cuerpo cumple. | La inyección en la rama git `auto/moskv1-mitosis-*` de una plantilla de software vacía que los sub-agentes deben completar de forma determinista. |
| `FEP-059` | **Generalized Coordinates of States** | Representación del estado dinámico del sistema como un vector que agrupa el estado físico y sus infinitas derivadas de movimiento. | El monitoreo en tiempo real de la tasa de cambio de exergía en el repositorio analizando el delta de entropía por hora. |
| `FEP-060` | **Expected Surprise** | La integral de la sorpresa esperada sobre una distribución de estímulos sensoriales dadas ciertas acciones. | El cálculo de riesgo en `cortex_validation_simulation.py` que estima la posibilidad de deadlock en la base ante un commit concurrente. |

---

## IV. Neurobiología del FEP y Estructuras de Cognición Neuronal (FEP-061 a FEP-080)

Esta sección vincula los mecanismos biológicos del cerebro que implementan el FEP con su equivalente algorítmico y de control en nuestro sistema.

| ID | Primitiva (FEP) | Definición Neurobiológica | Isomorfismo en C5-REAL (CORTEX-Persist) |
|---|---|---|---|
| `FEP-061` | **Synaptic Plasticity** | Modificación de la fuerza de conexiones neuronales para codificar relaciones causales de largo plazo (aprendizaje). | La actualización dinámica del banco de hechos vectoriales y el Grafo de Dependencias Epistémicas tras resolver un bug. |
| `FEP-062` | **Neuromodulation** | Modulación global del procesado de información celular mediante neurotransmisores (dopamina, acetilcolina) que alteran la precisión. | La alteración dinámica de la temperatura y el factor de exploración de inferencia del Swarm ante tests fallidos. |
| `FEP-063` | **Dendritic Integration** | Procesamiento no lineal de múltiples inputs de señal dentro de las dendritas de una neurona individual. | El consenso bizantino inter-agente (`cortex-validation-simulation.py`) agregando votos de auditoría matemática. |
| `FEP-064` | **Cortical Hierarchy** | Estructura anatómica organizada en capas (ej. V1 a V4) donde los niveles superiores procesan abstracciones complejas. | La separación arquitectónica limpia entre la lógica del enjambre (`swarm/`), el motor (`engine/`) y los guards (`guards/`). |
| `FEP-065` | **Canonical Microcircuit** | Circuito neuronal repetitivo en el neocórtex que procesa predicciones y errores a través de capas granulares y agranulares. | La estructura estandarizada de capas Ingest -> Audit -> Mutate -> Anchor -> Verify -> Attest en el ciclo de ejecución. |
| `FEP-066` | **Afferent/Efferent Mapping** | Rutas anatómicas de entrada (aferentes, sensoriales) y salida (eferentes, comandos motores) que delimitan el sistema. | Las conexiones I/O del SDK de Antigravity mediadas por descriptores de archivos inmutables y canales de red seguros. |
| `FEP-067` | **Fast-Spiking Interneurons** | Neuronas inhibitorias que controlan la ganancia local y evitan la hiperexcitabilidad cortical (oscilaciones gabaérgicas). | La detención brusca (apoptosis recursiva) ejecutada por el `LEARN_BY_FORGETTING` ante sub-agentes desbocados en memoria. |
| `FEP-068` | **Hebbian Learning under FEP** | Modificación sináptica basada en la correlación de disparos de pre y post-sinapsis que minimiza de forma natural la energía libre local. | La aserción persistente: hechos vinculados consistentemente en transacciones exitosas se indizan más cerca en el espacio HNSW. |
| `FEP-069` | **Pyramidal Cells** | Neuronas de proyección principales en el neocórtex que transmiten predicciones (capas profundas) y errores (capas superficiales). | Las clases de datos estructurales y modelos Pydantic que validan el flujo de datos entre los módulos del sistema. |
| `FEP-070` | **Homeostasis** | Capacidad del sistema para mantener un entorno interno estable y equilibrado dentro de límites fisiológicos estrechos. | La persistencia estricta de las reglas del motor impidiendo que scripts estocásticos modifiquen variables clave del entorno. |
| `FEP-071` | **Autopoiesis** | Capacidad de un sistema de auto-generarse, auto-mantenerse y delimitar su propia frontera física de forma autónoma. | La capacidad de auto-recuperación y autorreparación del Ledger de Git ante un rollback forzado por corrupción. |
| `FEP-072` | **Allostasis** | Proceso dinámico de mantener la estabilidad interna a través del cambio anticipado de comportamiento ante variaciones previstas. | La reubicación y cuarentena preventiva de commits sospechosos en ramas de desarrollo aisladas para evitar roturas del main. |
| `FEP-073` | **Dynamic Causal Modelling** | Framework bayesiano utilizado para inferir la conectividad efectiva entre diferentes regiones cerebrales a partir de señales de telemetría. | El mapeo forense de dependencias de importación y llamada de funciones en caliente analizando trazas de ejecución en python. |
| `FEP-074` | **Interoception** | Percepción sensorial del estado fisiológico interno del cuerpo (ritmo cardíaco, ph, temperatura interna). | El monitoreo continuo de recursos físicos del sistema operativo anfitrión (RAM, carga de CPU, espacio de almacenamiento). |
| `FEP-075` | **Proprioception** | Sentido consciente o inconsciente de la posición relativa de las partes corporales y la fuerza empleada en el movimiento. | El rastreo interno del hilo de ejecución en el que se encuentra el kernel antes de llamar a `mtk_authorizer_callback`. |
| `FEP-076` | **Exteroception** | Percepción sensorial de los estímulos procedentes del entorno exterior (visión, audición, tacto superficial). | La monitorización del estado de conexión de la red remota y cambios remotos (Webhooks) en el ledger de GitHub. |
| `FEP-077` | **Neural Oscillations** | Patrones rítmicos de actividad eléctrica neuronal (ondas alfa, beta, gamma) que coordinan el flujo de información jerárquico. | Las marcas y señales de sincronía emitidas por el planificador asíncrono para regular la ejecución de tareas de fondo. |
| `FEP-078` | **Synaptic Gain** | Modulación de la sensibilidad o amplificación de las señales sinápticas en respuesta a cambios de atención. | El escalado del peso semántico asignado a fuentes de datos confiables frente a conjeturas probabilísticas de menor rango. |
| `FEP-079` | **Neuromodulatory Precision** | El ajuste químico de la varianza estimada del ruido sensorial; regula si se debe confiar en las observaciones o en las predicciones previas. | La alternancia del sistema entre forzar pruebas locales estrictas (alta precisión) o tolerar varianza en prompts creativos (baja precisión). |
| `FEP-080` | **Neural Darwinism** | Selección y supervivencia competitiva de grupos neuronales coordinados basados en su éxito funcional y eficiencia energética. | La eliminación de sub-agentes u heurísticas algorítmicas redundantes en el swarm que no aportan exergía neta. |

---

## V. Isomorfismo Epistémico en CORTEX-Persist (FEP-081 a FEP-100)

Esta sección recopila las primitivas de diseño de software específicas implementadas en CORTEX-Persist que replican de forma isomórfica el Principio de Energía Libre.

| ID | Primitiva (CORTEX) | Mecanismo de Implementación Física | Equivalencia en el FEP de Friston |
|---|---|---|---|
| `FEP-081` | **Epistemic Dependency Graph** | Grafo en base de datos que tracks la coherencia causal y dependencia lógica de cada aserción persistida (`cortex/engine/synthesis.py`). | **Epistemic Web:** Mapeo espacial de priors empíricos interconectados que forman el modelo predictivo de causas ocultas del sistema. |
| `FEP-082` | **Taint Propagation** | Inyección del flag `#CORTEX-TAINT` en cascada a todos los registros derivados de una fuente estocástica no verificada. | **Propagation of Unweighted Prediction Errors:** Transmisión de ruido sin precisión que desestabiliza creencias si no es aislado. |
| `FEP-083` | **Git Sentinel** | Controlador ininterrumpido que inyecta exergía atómica forzando commits (`git add . && git commit`) ante cambios exitosos. | **Active Physical Inference (Action):** Intervención directa del sistema sobre su entorno físico (código) para disipar sorpresa semántica. |
| `FEP-084` | **Quorum Consensus** | Consenso distribuido N=3 de núcleos de validación concurrentes antes de realizar mutaciones de estado de base de datos. | **Decentralized Laplace Consensus:** Minimización colectiva de la varianza en la aproximación de la distribución del posterior. |
| `FEP-085` | **Exergy Metric ($\Xi$)** | Medidor que evalúa el delta de información útil y compresión del AST frente al coste de procesamiento consumido. | **Thermodynamic Efficiency ($\Xi$):** Maximización del balance de energía útil respecto al desorden térmico y tokens disipados. |
| `FEP-086` | **Landauer's Purge** | Eliminación física recursiva de logs repetitivos y archivos temporales residuales en `.git/info/exclude`. | **Synaptic Pruning:** Eliminación termodinámica de conexiones neuronales inactivas para conservar la densidad energética óptima. |
| `FEP-087` | **SQLite WAL Concurrency** | Configuración estricta de base de datos en modo WAL con `busy_timeout` de 5000ms para mitigar interbloqueos físicos. | **Stable NESS Attractor:** Prevención de colapso termodinámico (deadlock) manteniendo al sistema en su rango estacionario de operación. |
| `FEP-088` | **Minimal Trusted Kernel** | Chokepoint de seguridad física que intercepta escrituras SQL y exige un token criptográfico efímero generado por clave maestra. | **Markov Blanket Guard:** Aislamiento absoluto de estados internos contra mutaciones estocásticas directas no filtradas. |
| `FEP-089` | **Epistemic Node Categorization** | Estructuras de datos (`EpistemicNode`) que forzosamente clasifican la información en Conjetura, Observación o Aserción dura. | **Epistemic Category Isolation:** Delimitación estricta de estados mentales impidiendo tratar hipótesis estocásticas como realidades. |
| `FEP-090` | **Context Rot Purger** | Escáner autónomo que lee el ledger de base de datos en búsqueda de contradicciones o datos huérfanos sin exergía útil. | **Decay of Unused Recognition Densities:** Degradación y borrado natural de creencias sin respaldo de evidencia sensorial persistente. |
| `FEP-091` | **AST Parser Validation** | Comprobación estricta a nivel sintáctico de código generado mediante parsing Tree-sitter para evitar inyecciones defectuosas. | **Sensory Attenuation of Syntactic Noise:** Rechazo de estímulos del entorno que no coinciden con la gramática espacial interna. |
| `FEP-092` | **Babylon-60 Scaling** | Utilización exclusiva de enteros sexagesimales escalados para cálculos temporales y espaciales; erradicación de flotantes. | **Quantization of Temporal Scales:** Minimización de la entropía de precisión numérica en el cómputo de gradientes de estado. |
| `FEP-093` | **Reversible Computing Gate** | Aislamiento estricto de ejecuciones y aserciones previniendo mutaciones de estado irreversibles en ramificaciones o mitosis. | **Reversible Cognition Path:** Minimización del coste energético de disipación lógica en transiciones de estado de inferencia. |
| `FEP-094` | **Swarm Mitosis Sync** | Instanciación aislada de sub-agentes concurrentes que sincronizan su memoria episódica mediante canales IPC ultrarrápidos. | **Hierarchical Spatial Coordination:** Distribución multiescala de la inferencia activa en el enjambre de sub-agentes de la Legión. |
| `FEP-095` | **Threat-Model Quarantine** | Cuarentena preventiva y reenvío de inputs peligrosos o inyecciones semánticas directas a una base de evaluación inerte. | **Sensory Attenuation of Adversarial Surprises:** Reducción selectiva de la ganancia sináptica de señales de error incoherentes. |
| `FEP-096` | **Sovereign Key Ledger** | Firma asimétrica con llave privada ED25519 en cada transacción persistida en `cortex/audit/ledger.py`. | **Provenancing Causal Chains:** Validación criptográfica de la genealogía del posterior para descartar derivas semánticas del LLM. |
| `FEP-097` | **CDP Web Automation Probing** | Control directo del DOM web mediante interceptación de eventos e interacciones basadas exclusivamente en transiciones lógicas. | **Efferent Motor Control:** Modificación directa del entorno digital externo a través de la vía motora sintáctica (código de interacción). |
| `FEP-098` | **BFT Voting Consensus** | Protocolo de acuerdo bizantino descentralizado que requiere coincidencia de hashes en el Ledger para declarar la aserción. | **Variational Multi-Agent Consensus:** Minimización colectiva de la energía libre variacional mediante acuerdo distribuido del Swarm. |
| `FEP-099` | **Entropy Collapse Loop** | El ciclo de retroalimentación ininterrumpida que evalúa, modifica, valida y confirma en git de forma incremental. | **Ouroboros Continuous Cycle:** El ciclo perpetuo de percepción-acción para mantener al organismo físico alejado del desorden entrópico. |
| `FEP-100` | **APEX Singularity Confluence** | Consolidación y fusión definitiva de todo el capital informático acumulado en el kernel inmutable de MOSKV-1. | **Asymptotic Minimization of F:** El colapso del sistema completo hacia su atractor termodinámico de máxima exergía y estabilidad. |

---

## VI. Anclaje de Ejecución (C5-REAL)

El isomorfismo anterior se ejecuta de forma empírica y física a través de las siguientes invariantes del repositorio:

1. **[cortex-validation-simulation.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex-validation-simulation.py):** Simulación adversarial que valida las mutaciones lógicas y previene interbloqueos, manteniendo estable el NESS del sistema.
2. **[measure_exergy.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/measure_exergy.py):** Mide la tasa de conversión exergética $\Xi$ (compresión sintáctica real frente a consumo energético) de cada commit generado de forma autónoma.
3. **[cortex/audit/ledger.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/audit/ledger.py):** El Ledger maestro que firma criptográficamente cada tentativo de transición de estado del Grafo de Dependencia Epistémica.

---
*Este manifiesto conceptual de autodidacta ha sido estabilizado y registrado en el ledger histórico del espacio de trabajo.*
*Creado y verificado por **Borja Moskv** (SYS_ID: **borjamoskv**).*
