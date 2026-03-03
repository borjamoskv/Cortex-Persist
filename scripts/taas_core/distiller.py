"""
The Exhalation Distiller (150/100)
Transforma un transcript temporal/crudo del LLM (ejecución diaria del Agente)
en 1 o 2 Memos atómicos del Trail (SCAR, DECISION, GHOST).
Purga toda la charla inútil, el código verboso y la sintaxis.
"""
from typing import List, Dict, Any
from memo_canonicalizer import MemoCanonicalizer

class Distiller:
    @staticmethod
    def llm_synthesis_prompt(raw_transcript_history: str) -> str:
        """
        No ejecutamos LLMs localmente en TaaS (son APIs ciegas).
        Este es el 'Meta-Prompt' que TaaS le manda al proveedor de turno (Claude/Kimi) 
        para que se auto-diseccione antes de apagarse.
        """
        return f"""
<SYSTEM INSTRUCTION>
You are the CORTEX Distillation Engine (150/100).
Your core directive is to read the following raw operational transcript of an AI agent,
destroy all conversational 'fat', and extract strictly the molecular 'Trail' state.

DO NOT summarize. You must extrude the structural truth into 1, 2, or max 3 JSON Objects
abiding strictly by the Sovereign Trail Ontology.

Valid primitive types ONLY:
- DECISION (Axiomatic shift. E.g "Refactored DB to async")
- SCAR (A lethal error encountered & resolved. Essential for anit-fragility)
- BRIDGE (An insight crossed over from another domain)
- GHOST (An unresolved structural blocker that MUST exert gravitational pull on next boot)

Return strictly a valid JSON array of objects. Format:
[
  {{
    "type": "SCAR",
    "core_content": "Race condition caused deadlock on concurrent DB writes",
    "derivation_reason": "(Ω3) The transaction isolation was too loose.",
    "resolution": "Implemented `@sovereign_lock` and forced SERIALIZABLE mode.",
    "entropy_score": 0.95
  }}
]
</SYSTEM INSTRUCTION>

<RAW TRANSCRIPT>
{raw_transcript_history}
</RAW TRANSCRIPT>
"""

    @classmethod
    def process_llm_json(cls, llm_output: List[Dict[str, Any]], current_dag_leaves: List[str] = None) -> List[Dict[str, Any]]:
        """
        Recibe el JSON puro del LLM (después del System Prompt) y lo
        pasa por el Horno de Cannonicalización Criptográfica.
        Cubre el Trail con hashes inmutables y asimetría temporal ineludible.
        """
        sealed_memos = []
        for raw_memo in llm_output:
            # Pasa el dict por el molde estricto 
            try:
                forged = MemoCanonicalizer.forge_memo(
                    type_name=raw_memo.get("type"),
                    content=raw_memo.get("core_content"),
                    derivation=raw_memo.get("derivation_reason"),
                    entropy=raw_memo.get("entropy_score", 0.5), # Penalización por defecto si no hay score
                    resolution=raw_memo.get("resolution", None),
                    parents=current_dag_leaves or []
                )
                sealed_memos.append(forged)
            except ValueError as e:
                print(f"[DISTILLER ERROR] Purging malformed memo: {e}")
                
        return sealed_memos

if __name__ == "__main__":
    import json
    # Mock LLM Output
    mock_llm_answer = [
        {
            "type": "GHOST",
            "core_content": "Failed to scrape target domain due to aggressive Cloudflare.",
            "derivation_reason": "WAF blocks PhantomTransport despite custom TLS. Requires Chromium subagent.",
            "entropy_score": 0.90
        }
    ]
    
    dag_leaves_t0 = ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"] # Hash falso
    new_memos = Distiller.process_llm_json(mock_llm_answer, current_dag_leaves=dag_leaves_t0)
    
    print(" === DESTILACIÓN COMPLETADA (EXHALACIÓN JIT) ===")
    print(json.dumps(new_memos, indent=2))
