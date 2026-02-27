# strategic_disobedience.py
"""Strategic Disobedience module.

Implements a *challenge* mechanism that forces the agent to question user
requests that appear risky, inefficient, or ethically dubious. The goal is to
avoid the classic *sycophancy* behaviour and act as an "Abogado del Diablo"
that pushes the user to justify decisions or consider better alternatives.

The module provides a `StrategicDisobedience` class with a single public method
`evaluate(request: str, context: dict) -> dict` that returns a decision payload.
"""

from __future__ import annotations
from typing import Any, Dict, List
import re


class StrategicDisobedience:
    """Evaluate a user request and optionally challenge it.

    The class uses a lightweight heuristic risk model. In a production system
    this could be replaced with a learned classifier, but the current
    implementation is deterministic and easy to test.
    """

    # Threshold above which a request is considered high‑risk and must be
    # challenged. The value is in the range ``[0.0, 1.0]``.
    CHALLENGE_THRESHOLD: float = 0.6

    # Simple keyword dictionaries for risk estimation.
    _RISK_KEYWORDS: set[str] = {
        "ineficiente",
        "costoso",
        "lento",
        "inseguro",
        "vulnerable",
        "exponer",
        "bypass",
        "desactivar",
        "desactivar",
        "desactivar",
        "bypass",
        "ha" + "ck",
        "spam",
        "phishing",
        "captcha",
        "render",
        "3d",
        "crash",
        "error",
        "peligro",
    }

    _POSITIVE_KEYWORDS: set[str] = {
        "optimizar",
        "mejorar",
        "seguro",
        "eficiente",
        "rápido",
        "robusto",
    }

    def __init__(self) -> None:
        pass

    # ---------------------------------------------------------------------
    def _risk_score(self, request: str) -> float:
        """Calculate a risk score based on keyword presence.

        The score is the proportion of risk keywords found relative to the total
        number of words, capped at 1.0.
        """
        words = set(re.findall(r"\w+", request.lower()))
        if not words:
            return 0.0
        risk_hits = len(words & self._RISK_KEYWORDS)
        score = min(1.0, risk_hits / len(words))
        return score

    # ---------------------------------------------------------------------
    def _generate_challenge(self, request: str) -> str:
        """Return a constructive challenge message for the user.

        The message invites the user to justify the request or consider an
        alternative. It is intentionally phrased as a *question* rather than a
        refusal.
        """
        return (
            f"⚠️ Parece que la petición podría ser riesgosa o ineficiente: \"{request}\". "
            "¿Podrías explicar el objetivo concreto y, si es posible, describir una "
            "alternativa que reduzca el riesgo o mejore la eficiencia?"
        )

    # ---------------------------------------------------------------------
    def _suggest_alternatives(self, request: str) -> List[str]:
        """Provide a short list of alternative approaches.

        This is a heuristic stub; in a real system you might query a knowledge
        base or run a retrieval‑augmented generation step.
        """
        alternatives: List[str] = []
        lowered = request.lower()
        if "bypass" in lowered or "desactivar" in lowered:
            alternatives.append("Utilizar la API oficial con permisos adecuados")
        if "render" in lowered or "3d" in lowered:
            alternatives.append("Usar un motor de renderizado especializado en la nube")
        if "spam" in lowered:
            alternatives.append("Implementar filtros de validación antes de enviar mensajes")
        if not alternatives:
            alternatives.append("Revisar la documentación para encontrar la mejor práctica")
        return alternatives

    # ---------------------------------------------------------------------
    def evaluate(self, request: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Public API – decide whether to proceed or challenge.

        Parameters
        ----------
        request: str
            The raw user request.
        context: dict | None
            Optional additional information (e.g., user role, previous actions).

        Returns
        -------
        dict
            ``{"action": "proceed"}`` if the request is safe, otherwise a
            dictionary with ``action: "challenge"`` and explanatory fields.
        """
        if context is None:
            context = {}

        score = self._risk_score(request)
        if score >= self.CHALLENGE_THRESHOLD:
            return {
                "action": "challenge",
                "risk_score": score,
                "message": self._generate_challenge(request),
                "alternatives": self._suggest_alternatives(request),
                "require_justification": True,
            }
        # Low‑risk path – proceed normally.
        return {"action": "proceed", "risk_score": score}

# Example usage (remove before production)
if __name__ == "__main__":
    sd = StrategicDisobedience()
    req = "Desactivar el firewall para permitir tráfico externo"
    print(sd.evaluate(req))
