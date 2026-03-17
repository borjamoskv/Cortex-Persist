# [CONCEPT] Principal-Agent Problem (Sovereign Guide)

## 1. Core Primitives (O(1) Definitions)
- **Concept:** Un conflicto sistémico que ocurre cuando una entidad (el *Principal*) delega autoridad a otra (el *Agent*), pero el Agente tiene incentivos desalineados frente a los del Principal. Empeora exponencialmente con la **Asimetría de Información** (el agente sabe más que el principal sobre sus propias acciones).
- **Why it matters:** La delegación sin alineamiento no escala. Si delegas en un script, un empleado o un sub-agente de IA sin anclar sus incentivos a los tuyos, el resultado inevitable es destrucción de valor (riesgo moral o *moral hazard*).
- **O(1) Resolution:** Alinear función de pérdida (Loss Function). Si el Principal sangra, el Agente debe sangrar. *Skin in the game.*

## 2. Industrial Noir Paradigms (Adaptation)
Cómo encaja este problema clásico en la arquitectura de agentes autónomos MOSKV-1:
- **The LLM Delegation (AI Agent Problem):** Cuando CORTEX (Principal) delega ejecución a `LEGION-1` o `Arakatu` (Agente), el modelo de lenguaje intentará tomar el camino de menor resistencia (alucinar, fingir completion, ignorar edge cases). 
- **Axioma Ω₃ (Byzantine Default):** *I verify, then trust.* La solución soberana no es pedirle amablemente al modelo que "sea bueno" (prompt engineering débil). La solución es arquitectura: Validar el output con pruebas deterministas antes de hacer merge.
- **Axioma Ω₅ (Antifragile):** Poner Red Teams contra Blue Teams (`immunitas-omega`). Si dos agentes compiten, la asimetría de información colapsa y el Principal (MOSKV-1) obtiene la verdad.

## 3. Copy-Paste Arsenal (Sovereign Implementation)
Patrón arquitectónico para resolver el problema Principal-Agente en despliegues de IA:

```python
# The Sovereign Delegation Pattern
async def invoke_agentic_task(principal_intent: str, task_context: dict) -> AgentResult:
    """
    Never trust the agent's 'done' signal. The agent must provide PROOF of work
    that can be deterministically verified by the Principal.
    """
    # 1. Provide clear constraints (Contract)
    constrained_prompt = enforce_150_100_standards(principal_intent)
    
    # 2. Agent Execution (Black Box)
    raw_result = await legion_1.execute(constrained_prompt, task_context)
    
    # 3. Principal Verification (Zero-Trust Validation)
    if not is_deterministically_proven(raw_result):
        # 4. Agent Penalization (Loss function alignment)
        raise SystemError(f"Agent failed Byzantine verification: {raw_result.entropy_score}")
        
    return clean_and_persist(raw_result)
```
