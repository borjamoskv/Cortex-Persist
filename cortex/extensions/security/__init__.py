# [C5-REAL] Exergy-Maximized
"""CORTEX security package exports.

Keep package import lightweight so callers can access specific submodules
like tenant/signatures without importing the full security stack.
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from .abac import ABACEvaluator, Policy
except (ValueError, TypeError, OSError, KeyError):
    ABACEvaluator = None  # type: ignore[assignment]
    Policy = None  # type: ignore[assignment]
else:
    __all__ += ["ABACEvaluator", "Policy"]

try:
    from .anomaly_detector import AnomalyDetector
except (ValueError, TypeError, OSError, KeyError):
    AnomalyDetector = None  # type: ignore[assignment]
else:
    __all__.append("AnomalyDetector")

try:
    from .honeypot import HONEY_POT, HoneypotManager
except (ValueError, TypeError, OSError, KeyError):
    HONEY_POT = None  # type: ignore[assignment]
    HoneypotManager = None  # type: ignore[assignment]
else:
    __all__ += ["HONEY_POT", "HoneypotManager"]

try:
    from .injection_guard import InjectionGuard
except (ValueError, TypeError, OSError, KeyError):
    InjectionGuard = None  # type: ignore[assignment]
else:
    __all__.append("InjectionGuard")

try:
    from .integrity_audit import IntegrityAuditor
except (ValueError, TypeError, OSError, KeyError):
    IntegrityAuditor = None  # type: ignore[assignment]
else:
    __all__.append("IntegrityAuditor")

try:
    from .security_sync import SIGNAL, SecurityVisualSync
except (ValueError, TypeError, OSError, KeyError):
    SIGNAL = None  # type: ignore[assignment]
    SecurityVisualSync = None  # type: ignore[assignment]
else:
    __all__ += ["SIGNAL", "SecurityVisualSync"]

try:
    from .signatures import Ed25519Signer, get_default_signer
except (ValueError, TypeError, OSError, KeyError):
    Ed25519Signer = None  # type: ignore[assignment]
    get_default_signer = None  # type: ignore[assignment]
else:
    __all__ += ["Ed25519Signer", "get_default_signer"]

try:
    from .tenant import get_tenant_id, tenant_id_var
except (ValueError, TypeError, OSError, KeyError):
    get_tenant_id = None  # type: ignore[assignment]
    tenant_id_var = None  # type: ignore[assignment]
else:
    __all__ += ["get_tenant_id", "tenant_id_var"]

try:
    from .threat_feed import ThreatFeedEngine
except (ValueError, TypeError, OSError, KeyError):
    ThreatFeedEngine = None  # type: ignore[assignment]
else:
    __all__.append("ThreatFeedEngine")
