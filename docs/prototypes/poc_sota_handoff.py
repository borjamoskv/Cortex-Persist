import asyncio
import logging

from cortex.extensions.hypervisor.belief_object import BeliefConfidence, BeliefObject
from cortex.extensions.llm.cognitive_handoff import CognitiveHandoff

# Silenciar logs genéricos para claridad en el POC
logging.getLogger("cortex.extensions.llm.cognitive_handoff").setLevel(logging.WARNING)

class MockRouter:
    async def route(self, prompt, provider_hint=None):
        intent = prompt.intent.value if prompt.intent else 'N/A'
        mode = prompt.reasoning_mode.value if prompt.reasoning_mode else 'N/A'
        
        print(f"\n[MockRouter] 🔹 Nodo Invocado | Intent: {intent}")
        print(f"[MockRouter] ⚙️ Reasoning Mode: {mode}")
        print(f"[MockRouter] 🚀 Provider Físico Asignado: {provider_hint}")
        
        class MockResult:
            def __init__(self, tokens):
                self.tokens_used = tokens
                
        # Simulamos comportamiento de los LLMs
        if intent == "episodic_processing":
            print("[MockRouter] ↳ Resultado: Prescreen completado. Relevancia alta.")
            return MockResult(12)
            
        elif intent == "belief_audit":
            if provider_hint == "z_ai":  # Auditor Económico (GLM-5.2)
                print("[MockRouter] ↳ Auditor Económico dictamina: UNCERTAIN (Forzando escalada P0)")
                return MockResult(150)
            elif provider_hint == "anthropic":  # Auditor Premium (Opus 4.8)
                print("[MockRouter] ↳ Auditor Premium dictamina: CERTAIN sin contradicciones (Axioma preservado)")
                return MockResult(600)
                
        return MockResult(10)

async def main():
    print("==========================================================")
    print(" 💠 POC: CORTEX COGNITIVE HANDOFF (SOTA 2026-06) 💠")
    print("==========================================================")
    
    # Instanciar el orquestador modificado
    handoff = CognitiveHandoff(router=MockRouter())
    
    # Generar un Belief (Conjetura generativa a evaluar)
    belief = BeliefObject(
        content="La red neural de Autodidact debe rutear la carga estructural a arquitecturas MIT para optimización termodinámica.",
        project="cortex-core",
        tenant_id="poc",
        confidence=BeliefConfidence.C3_PROBABLE
    )
    
    print(f"\n[+] Ingiriendo Fact: '{belief.content}'")
    
    # Ejecutar la cascada
    verdict = await handoff.process_belief(belief)
    
    print("\n==========================================================")
    print(" 🏁 COLAPSO CAUSAL COMPLETADO")
    print("==========================================================")
    print(f" Acción Final:   {verdict.action.value}")
    print(f" Consumo (Tks):  {verdict.cost_tokens}")
    print(f" Razón:          {verdict.reason}")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(main())
