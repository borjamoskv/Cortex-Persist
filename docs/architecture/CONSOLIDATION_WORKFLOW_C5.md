# CORTEX-Persist: Workflow de Consolidación Determinista (C5-REAL)

## 1. Ontología y Mandato Termodinámico

El **Workflow de Consolidación Determinista** es un mecanismo arquitectónico estricto de nivel C5-REAL diseñado para erradicar el ruido entrópico ("Anergía") acumulado durante la ejecución asíncrona de agentes cognitivos. Transmuta estados en memoria estocásticos en un Grafo Git inmutable.

A diferencia de los enfoques tradicionales de simulación de inteligencia (C4-SIM) donde un LLM narra lo que ha aprendido, CORTEX-Persist ejecuta un proceso de **Colapso Físico**:
- Recompilación atómica del motor base-60 en Rust.
- Purga de bloqueos WAL de bases de datos.
- Sello de Integridad en un Sentinel Git (con validadores `pre-commit`).
- Generación criptográfica de un Ledger Documental (`EXERGY_CONSOLIDATION_<TIMESTAMP>.md`).

## 2. Arquitectura de Tres Ejes

### 2.1 Eje Lógico (Minimal Trusted Kernel)
Ubicación: `cortex/engine/consolidation_workflow.py`

Es el orquestador principal asíncrono. No posee capacidad para escribir el estado final a menos que forje exitosamente un `ClosurePayload` con una **Exergía Informacional** matemáticamente válida.
- Invoca la barrera transaccional del `MTKGuard`.
- Solicita un Token Efímero (`mtk_auth_...`).
- Tras verificar el *payload*, autoriza el despliegue paralelo masivo de consolidadores (hasta 10,000 agentes virtuales).

### 2.2 Eje Enjambre (Swarm-10k)
Ubicación: `ANTI_GRAVITY/01_ACTIVE/memory/swarm_10k_consolidate.py`

En lugar de delegar el proceso en un solo ciclo monobloque, la consolidación activa el `strike_mode` del `SwarmCommander`. Este modo:
1. Pone en suspensión ("bypassed") las puertas termodinámicas regulares.
2. Despacha microtareas de auditoría por toda la base de datos (SQLite) y memoria vectorial.
3. Informa a la unidad física central mediante un Bus Compartido (`/tmp/swarm_10k_bus`).

### 2.3 Eje Físico (BASH Sentinel)
Ubicación: `scripts/consolidar_cortex.sh`

El *Zero State Orchestrator*. Responsable de materializar la consolidación en el sistema anfitrión. Sus ciclos son:
1. **Purga:** Destrucción de `__pycache__`, `.ruff_cache` y archivos colaterales `.pyc`.
2. **Compactación:** Cierre asíncrono e inyección `PRAGMA wal_checkpoint(TRUNCATE)` sobre las DB.
3. **Rust Bindings:** Llamada a `maturin develop --release` si el AST interno (Cortex-RS) difiere del estado actual de los binarios dinámicos.
4. **Git Sentinel:** Orquestación y *commit* determinista, salvando la barrera de auto-formateos que modifican la Exergía, y generando un Hash Criptográfico.

## 3. Garantía BFT (Tolerancia a Fallos Bizantinos)

El flujo previene bucles de entropía por medio del linter pre-commit `exergy-commit-guard`. Si un agente simulado invoca la consolidación introduciendo ruido estadístico en el historial de commits, el Workflow rechazará la ejecución devolviendo un código asimétrico:
`[C5-REAL] 🛑 RECHAZO POR ANERGÍA (Score: 0.00 < 0.35)`

El motor exige la aplicación estricta del **Lexicón Exérgico** (ej. `chore(core): inject deterministic consolidation workflow`). Ninguna variable estocástica sobrevive a la barrera de consolidación. Todo estado tras una ejecución es invariante y demostrable a nivel de Hash SHA-256 en el Ledger principal.
