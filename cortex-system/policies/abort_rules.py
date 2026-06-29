"""
C5-REAL: Abort Rules Policy
Author: Borja Moskv / borjamoskv
"""

from typing import Any


class AbortRules:
    @staticmethod
    def evaluate(metrics: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluates metrics against strict C5-REAL thresholds.
        Returns a dict with {"abort": bool, "reason": str}
        """
        originality = metrics.get("originality_raw", 1.0)
        friction = metrics.get("friction_ms", 0.0)
        attention = metrics.get("attention_yield", 1.0)

        # Strict rules thresholds
        if originality < 0.20:
            return {
                "abort": True,
                "reason": f"Originality ratio ({originality:.2f}) falls below absolute limit of 0.20."
            }

        if friction > 180000:  # 3 minutes
            return {
                "abort": True,
                "reason": f"Execution friction ({friction} ms) exceeds limit of 180000 ms."
            }

        if attention < 0.35:
            return {
                "abort": True,
                "reason": f"Attention yield ({attention:.2f}) falls below survival limit of 0.35."
            }

        return {"abort": False, "reason": "Stable operational thresholds."}
