<!-- [C5-REAL] Exergy-Maximized -->
# ⚙️ CORTEX KERNEL SPEC v6: C5-REAL OPERATIONAL REALITY

Esta especificación anula cualquier metáfora, entidad abstracta o "Agentic Mysticism" previo (el antiguo PANTHEON). Todo lo definido aquí mapea estrictamente a una función, un struct, un bus o un hash criptográfico.

## 0. C5-REAL CORE RULES (HARD CONSTRAINTS)

1. **No narrative claims without executable trace:** Si no se puede compilar o ejecutar, no existe.
2. **No agent exists without identity + key + event log:** Todo agente es un Struct con Key Material.
3. **No metric exists without unit + measurement method:** Rendimiento medible empíricamente, no en promesas abstractas.
4. **No propagation exists without explicit channel:** La propagación entre proyectos cruza por Webhooks, Diff Pipelines o Event Bus.
5. **No system state exists without hashable snapshot:** El estado es inmutable y recuperable (`ROLLBACK_STATE`).
6. **All failure defaults to HARD FAIL:** Sin reinterpretación narrativa de errores. El SAGA aborta y retrocede.

---

## 1. ORQUESTACIÓN Y LATENCIA (C5_SCHEDULER)
El corazón del Kernel. Mapea la intención de ejecución a ciclos de la máquina.

- **`cortex.scheduler.async_loop` (Ex-Apotheosis/Keter):**
  - **Función:** Bucle de orquestación lock-free para dispatch de agentes.
  - **Latencia Objetivo:** Microsecond Lock-Free Latency (vía `ZeroCopyRingBuffer` y Rust-FFI). *Nota: La "latencia negativa" es físicamente imposible y se repudia formalmente.*
  - **Métrica:** Dispatch latency medido en microsegundos; Throughput medido en agent-events/sec.
  - **Fallo:** OOM o Timeout -> SAGA-1 Abort.

## 2. COMPILADOR DE REALIDAD (C5_JIT_COMPILER)
El sistema que transforma intenciones crudas en DAGs (Directed Acyclic Graphs) accionables.

- **`cortex.engine.synthesis.JIT_Compiler` (Ex-Demiurge):**
  - **Función:** Parseo de input, inyección de dependencias y generación de `Task_DAG`.
  - **Estado:** Carga perfiles (Skills) verificables desde `.gemini/config/skills`.
  - **Verificación:** Si el DAG generado carece de un nodo sumidero (Sink) que mute el estado en el Ledger, se descarta por Limerencia Epistémica.

## 3. MUTACIÓN DE ESTADO IRREVERSIBLE (C5_STATE_MUTATION)
La única forma de alterar la realidad del repositorio.

- **`cortex.engine.crystallizer.Crystallizer` (Ex-Void/Ouroboros):**
  - **Función:** Escribe en disco, en SQLite WAL y en el Ledger.
  - **Causalidad:** Exige una prueba criptográfica (`CORTEX-TAINT`). Sin firma del Agente (Struct + Key Material), la mutación se rechaza.
  - **Compresión:** Elimina código muerto basándose estrictamente en el AST. No hay "densidad infinita"; hay Entropía de Shannon Mínima.

## 4. PROPAGACIÓN Y CONSENSO (C5_SWARM_BUS)
El transporte para la inteligencia distribuida.

- **`cortex.consensus.byzantine_bus` (Ex-Legion/Nexus):**
  - **Función:** Transmisión de estado y deltas de código entre agentes y proyectos.
  - **Canal Explícito:** Utiliza un bus de eventos en memoria (Redis/RingBuffer) o IPC. La "telepatía inter-proyecto" está estrictamente mapeada a un **Version Propagation Layer** (Git Patches cruzados).
  - **Hard Fail:** Si no hay Quorum (N=3 aserciones exitosas), la mutación es bloqueada en la Frontera Bizantina.
