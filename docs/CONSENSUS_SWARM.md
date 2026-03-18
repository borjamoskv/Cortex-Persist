# CORTEX Consensus & Thermodynamics (Hito 4: Byzantine Routing)

> "A system that cannot quantify its own energy expenditure is a system that cannot survive its own complexity."
> — CORTEX Axiom Ω₁

La toma de decisiones en el Enjambre CORTEX no se confía a la elocuencia estocástica de un solo modelo fundacional. Se rige por restricciones termodinámicas (costo, latencia, redundancia en vuelo, compresión de información) y arquitecturas de tolerancia a fallos bizantinos (BFT).

---

## 1. El Enrutador Resiliente (`cortex/extensions/llm/router.py`)

CORTEX no habla directamente con un LLM; delega todo al `CortexLLMRouter`, que aplica tres membranas físicas:

### A. Fallback Cascade & A-Records
El router prioriza modelos según la afinidad de dominio (`intent`). Si la tarea es `REASONING`, buscará modelos frontera. 
Los modelos tienen **Cost Classes** (Free, Low, Medium, High). Si un modelo resuelve exitosamente sin fallos, el Router guarda un **A-Record** en memoria. En futuras llamadas con idéntico `intent`, el Router invoca directamente la ruta conocida (O(1) Hot Path), saltando latencia evaluativa.

### B. Thermal Heat-Sink (Coalescencia)
Si 140 agentes solicitan de forma simultánea idéntico prompt, enviar 140 peticiones a Gemini quema Presupuesto y excede el rate limit. El *Heat-Sink* genera un hash SHA-256 del `(instruction:memory:intent)`. La petición concurrentes número 2 al 140 esperan la resolución en memoria (`asyncio.Future`) de la primera petición. O(1) Termodinámico.

### C. Shannon Compression (Axiom Ω₁₃)
Si se excede el 90% de la ventana de contexto permitida por el modelo en la *Working Memory*, se evita el OOM truncando *strictamente* los mensajes intermedios, conservando siempre el *Seed Instruction* primero y los últimos *Tail Messages*.

---

## 2. Weighted Byzantine Fault Tolerance (WBFT - `cortex/consensus/byzantine.py`)

Cuando CORTEX necesita tomar decisiones de impacto arquitectónico, invoca a `N` modelos en paralelo y los somete a **WBFTConsensus**.

El sistema garantiza tolerancia si un tercio (o menos) de los modelos comienza a alucinar (`faulty/malicious nodes`).
1.  **Agreement Matrix**: Calcula la distancia de Jaccard entre todos los pares de *respuestas generadas*, formando un clúster mayoritario (Centroid).
2.  **Reputation Weights**: Los votos del consenso no son 1=1. Un modelo que históricamente acierta en la categoría actual (basado en un historial que decae matemáticamente) pondera más fuerte que un modelo de menor confiabilidad técnica.
3.  **Outlier Isolation**: Si un modelo produce una respuesta elegante pero muy apartada del centroide semántico (`Outlier Threshold = 0.15`), el sistema etiqueta al nodo como defectuoso (`is_outlier = True`) e ignora su conjetura.

---

## 3. Presupuesto Termodinámico (`extensions/swarm/budget.py`)

Para regir este volumen de inferencias concurrentes cruzadas (Heat-Sinks y WBFT), CORTEX implementa un Contable Soberano (`SwarmBudgetManager`).
El Ledger de SQLite guarda por `Mission ID`:
- Input Tokens y Output Tokens.
- Costo matemático en USD ($) basándose en la `COST_PRICING` del modelo utilizado.
- Cuenta de Peticiones.

**No hay Ouroboros sin contabilidad:** Si MEJORAlo y el Enjambre empiezan a entrar en un espiral de curación infinita, el Manager puede observar la métrica `total_cost_usd` en SQLite para interceder algorítmicamente y detener el gasto de *Exergy*.
