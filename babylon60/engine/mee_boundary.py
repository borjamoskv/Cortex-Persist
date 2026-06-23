import json
import re

import cortex_rs


def extract_event_from_text(text: str) -> dict:
    """
    Simula la frontera estocástica (LLM Function Calling).
    Interpreta lenguaje natural y devuelve el evento determinista.
    """
    # Expresión regular simple simulando la extracción de un LLM
    match = re.search(r'transfiere\s+(\d+)', text.lower())
    if match:
        amount = int(match.group(1))
        return {"delta": -amount}
    
    raise ValueError("LLM Error: Could not extract transfer intent from text.")

def commit_transfer(text: str, current_balance: int) -> dict:
    """
    Frontera de ejecución. 
    1. Llama al "LLM" (extract_event_from_text).
    2. Colapsa la incertidumbre invocando la matemática de BABYLON-60 en Rust.
    """
    # 1. Mundo Probabilístico
    event_dict = extract_event_from_text(text)
    state_dict = {"balance": current_balance}

    # 2. Transición al Mundo Determinista (C5-REAL)
    proof_json = cortex_rs.execute_mee_transfer(
        json.dumps(state_dict),
        json.dumps(event_dict)
    )

    # Devolvemos el ProofArtifact final
    return json.loads(proof_json)
