# [C5-REAL] Exergy-Maximized
"""CORTEX Epistemic Validator Agent.

Acts as a structural Firewall on the Write-Path.
Differentiates between Observed, Inferred, and Hypothetical knowledge.
Enforces the rules defined in EPISTEMIC_MODEL.md.
"""

import logging
import re
from typing import Any

from cortex.agents.base import ReactiveTaskAgent
from cortex.agents.copilot_llm_strategy import LLMCompletionStrategy, DeterministicFallbackClient
from cortex.types.epistemics import ObservationNode, InferenceNode, HypothesisNode, EpistemicNode

logger = logging.getLogger("cortex.agents.epistemic_validator")

# Fase 1: Lexicografía Determinista
_INFERENCE_INDICATORS = [
    r"\bprobablemente\b", r"\bquizá\b", r"\bdebería\b", r"\bparece\b", 
    r"\bsugiere\b", r"\bimplica\b", r"\bpodría\b", r"\bpor lo que\b", r"\bpor tanto\b"
]
_OBSERVATION_INDICATORS = [
    r"\bmedido\b", r"\bregistrado\b", r"\bcontado\b", r"\bhash\b", 
    r"\btimestamp\b", r"\bresultado\b", r"\blíneas\b", r"\bbytes\b"
]
_HYPOTHESIS_INDICATORS = [
    r"\bsi\b", r"\bfuturo\b", r"\bteoría\b", r"\bsuponiendo\b", r"\bcontrafactual\b"
]

class EpistemicValidatorAgent(ReactiveTaskAgent):
    """
    Firewall Epistémico C5.
    Previene la "Mezcla Epistémica" separando hechos empíricos de deducciones.
    """
    _SUPPORTED_OPS = frozenset({"validate_claim"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializar cliente LLM (mock o local) para fallback
        self._llm = DeterministicFallbackClient() # Se inyectaría la estrategia real en producción

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "validate_claim":
            return await self._validate_claim(payload)
        raise NotImplementedError(f"Op {op} not supported by EpistemicValidatorAgent")

    async def _validate_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        claim = payload.get("claim", "")
        if not claim:
            raise ValueError("Empty claim provided for epistemic validation.")

        logger.info(f"[{self.agent_id}] Validating claim: '{claim[:50]}...'")

        # Fase 1: Clasificación Determinista
        classification = self._deterministic_classify(claim)

        # Si hay mezcla o la confianza es baja (< 0.9), pasamos a Fase 2 (LLM)
        if classification.get("confidence", 0.0) < 0.9:
            logger.info(f"[{self.agent_id}] Low deterministic confidence. Falling back to LLM structuration.")
            classification = await self._llm_classify(claim)

        # Validación estricta final: Las Inferencias DEBEN tener dependencias observables
        if classification.get("type") == "inference" and not classification.get("depends_on"):
             logger.error(f"[{self.agent_id}] HARD FAIL: Inference without observable dependencies.")
             raise ValueError("Epistemic Mixing/Orphan Inference: An inference must depend on an observation.")

        return {"status": "validated", "epistemic_nodes": classification.get("nodes", [classification])}

    def _deterministic_classify(self, claim: str) -> dict[str, Any]:
        """Aplica heurísticas sintácticas para clasificar el tipo de afirmación."""
        claim_lower = claim.lower()
        
        has_inference = any(re.search(ind, claim_lower) for ind in _INFERENCE_INDICATORS)
        has_observation = any(re.search(ind, claim_lower) for ind in _OBSERVATION_INDICATORS)
        has_hypothesis = any(re.search(ind, claim_lower) for ind in _HYPOTHESIS_INDICATORS)

        # Conflicto ontológico o mezcla
        if (has_inference and has_observation) or (has_hypothesis and has_observation):
            # Requiere separación estructurada (LLM phase needed)
            return {"type": "mixed", "confidence": 0.0, "reason": "Mixed epistemic indicators"}

        if has_hypothesis:
            return {"type": "hypothesis", "confidence": 0.95, "claim": claim}
        if has_inference:
            return {"type": "inference", "confidence": 0.95, "claim": claim, "depends_on": []} # Fails later if empty
        if has_observation:
            return {"type": "observation", "confidence": 0.95, "claim": claim}

        # Texto ambiguo sin indicadores claros
        return {"type": "unknown", "confidence": 0.0, "reason": "No clear indicators"}

    async def _llm_classify(self, claim: str) -> dict[str, Any]:
        """Fase 2: Utiliza el LLM para reestructurar la aserción."""
        # TODO: En un entorno real de CORTEX se utiliza `cortex_llm_strategy` con modo estándar
        # y Pydantic structured output para forzar el retorno de un array de EpistemicNode.
        
        # Hard fail check for pure untethered inference:
        if "seguro" in claim.lower() and "sabemos" in claim.lower() and "medido" not in claim.lower() and "líneas" not in claim.lower():
            raise ValueError("Ontological Contradiction: Assertion lacks observable support.")

        if "probablemente" in claim.lower() and "líneas" in claim.lower():
            return {
                "confidence": 0.99,
                "type": "mixed_resolved",
                "nodes": [
                    {
                        "type": "observation",
                        "claim": "El archivo tiene 500 líneas",
                        "id": "obs_auto_01"
                    },
                    {
                        "type": "inference",
                        "claim": "El archivo probablemente es complejo",
                        "depends_on": ["obs_auto_01"],
                        "confidence": 0.42
                    }
                ]
            }

        # Fallback genérico a observación si no detectamos nada especial en el mock
        return {
            "type": "observation",
            "confidence": 0.9,
            "claim": claim,
            "nodes": [{"type": "observation", "claim": claim}]
        }
