# [C5-REAL] Exergy-Maximized
"""
Inyector de Realidad. Construye el bloque de contexto deduplicado desde claims verificados.
"""

import json

import cortex_core_rs


def build_verified_reality_context(ledger_path: str, max_claims: int = 50) -> str:
    """
    Construye un bloque de texto que contiene exclusivamente afirmaciones
    matemáticamente verificadas por el oráculo Rust, ordenadas por trust_score.
    """
    try:
        # Llama a load_verified_reality, que ya devuelve los claims ordenados y filtrados.
        verified_lines = cortex_core_rs.load_verified_reality(ledger_path)
    except Exception as e:
        return f"<cortex_verified_reality>\nERROR_LOADING_REALITY: {str(e)}\n</cortex_verified_reality>"
    
    seen_statements = set()
    deduplicated = []
    
    for line in verified_lines:
        try:
            claim = json.loads(line)
            statement = claim.get("input", {}).get("statement", "")
            if not statement or statement in seen_statements:
                continue
            
            seen_statements.add(statement)
            deduplicated.append(f"- [{claim.get('trust_score', 0.0):.2f}] {statement}")
            
            if len(deduplicated) >= max_claims:
                break
        except json.JSONDecodeError:
            continue
            
    if not deduplicated:
        return "<cortex_verified_reality>\nEMPTY_REALITY_REGISTRY\n</cortex_verified_reality>"
        
    context_block = "<cortex_verified_reality>\n"
    context_block += "\n".join(deduplicated)
    context_block += "\n</cortex_verified_reality>"
    
    return context_block
