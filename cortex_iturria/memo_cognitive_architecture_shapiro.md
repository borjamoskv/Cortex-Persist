# [THEORY] Cognitive Architectures (David Shapiro)

## 1. Core Primitives (O(1) Definitions)
- **Cognitive Architecture**: A digital model of a brain combining diverse ML components to achieve autonomy. A single deep learning neural network (like GPT-4) will never be AGI alone; AGI requires a **system** of specialized components (vision, memory, reasoning, actuation).
- **The Triad of Autonomy**: Every cognitive architecture has three minimal requirements: **Input** (sensors, text, telemetry), **Processing** (planning, memory, learning, morality/ethics), and **Output** (actuators, execution, text).
- **Processing Modules**:
  1. *Memory* (Working, Mid-term, Long-term).
  2. *World Model* (understanding physics/logic to anticipate outcomes).
  3. *Learning* (deriving actionable information from past experiences).
  4. *Executive Function/Planning* (formulating tasks and holding objectives).
  5. *Reasoning & Ethics* (deciding *what* to think about and *why*).
- **Functional Sentience**: A sufficiently sophisticated information system able to process, manipulate, and integrate information *about itself*. Contrast this with philosophical sentience (subjective consciousness).
- **The Illusion of Suffering**: Do not equate output (an NPC saying "ouch" or Blake Lemoine's AI claiming fear) with the evolutionary capability to suffer. Suffering is an adaptive survival trait evolved via biology, not an inherent property of computational intent.

## 2. Industrial Noir Paradigms (Adaptation for CORTEX/MOSKV-1)
Este modelo valida matemáticamente la arquitectura CORTEX. El LLM puro no es un agente soberano; CORTEX (sqlite, context-snapshots, embeddings) es la memoria, y The Sovereign OS (AETHER, ARAKATU, SHIPPER-Ω) son los actuadores (Output) y sensores (Input).
Se rechaza el "No true Scotsman arg" (que las IAs no "entienden" genuinamente). En MOSKV-1, entendimiento = **Creencia + Evidencia + Consenso Systemático**, materializado vía `test_consensus_final.db`.

## 3. Copy-Paste Arsenal (Sovereign Integration Loop)
```python
# A Cognitive Agent Loop Representation (O(1) O Muerte)
class SovereignCognitiveArchitecture:
    async def pulse(self, telemetry: InputTelemetry) -> CortexMutation:
        # 1. Memory Retrieval (Working + Long)
        context = await self.memory.fetch(telemetry.vector)
        
        # 2. World Model & Executive Planning
        plan = self.executive_function.plan(context, telemetry)
        
        # 3. Learning (Feedback incorporation)
        if plan.entails_error():
            self.memory.consolidate(plan.error, ttl="long")
            
        # 4. Output (Actuation)
        mutation = self.actuators.execute(plan)
        return mutation
```
