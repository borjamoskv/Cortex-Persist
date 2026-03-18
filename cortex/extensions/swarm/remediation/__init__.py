"""LEGION-Ω Remediation Swarm — 100 Agent Architecture.

50 Blue Team (remediation) + 50 Red Team (validation/siege).
Every Blue fix is siege-validated by its Red counterpart before persistence.
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    """Lazy import for remediation components."""
    if name == "LegionRemediationEngine":
        from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine

        return LegionRemediationEngine
    if name == "DiagnosisClassifier":
        from cortex.extensions.swarm.remediation.diagnosis import DiagnosisClassifier

        return DiagnosisClassifier
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "DiagnosisClassifier",
    "LegionRemediationEngine",
]
