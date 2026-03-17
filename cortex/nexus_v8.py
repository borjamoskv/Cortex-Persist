"""
CORTEX Nexus v8.1 — The Einstein-Rosen Bridge (Production Grade).

Legacy shim for backward compatibility. Use `cortex.nexus` directly.
"""

from cortex.extensions.nexus import (
    DomainOrigin,
    IntentType,
    NexusWorldModel,
    Priority,
    WorldMutation,
    mailtv_intercepted,
    moltbook_karma_laundered,
    moltbook_post_published,
    moltbook_shadowban_alert,
    sap_anomaly_detected,
)

__all__ = [
    "DomainOrigin",
    "IntentType",
    "Priority",
    "WorldMutation",
    "NexusWorldModel",
    "mailtv_intercepted",
    "moltbook_post_published",
    "moltbook_karma_laundered",
    "moltbook_shadowban_alert",
    "sap_anomaly_detected",
]
