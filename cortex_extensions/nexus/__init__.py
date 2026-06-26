# [C5-REAL] Exergy-Maximized
"""
CORTEX Nexus v8.1

Zero-latency trans-domain convergence layer.
"""

from cortex_extensions.nexus.convenience import (
    mailtv_intercepted,
    moltbook_karma_laundered,
    moltbook_post_published,
    moltbook_shadowban_alert,
    sap_anomaly_detected,
)
from cortex_extensions.nexus.db import NexusDB
from cortex_extensions.nexus.model import NexusWorldModel
from cortex_extensions.nexus.types import DomainOrigin, IntentType, Priority, WorldMutation

__all__ = [
    "DomainOrigin",
    "IntentType",
    "NexusDB",
    "NexusWorldModel",
    "Priority",
    "WorldMutation",
    "mailtv_intercepted",
    "moltbook_karma_laundered",
    "moltbook_post_published",
    "moltbook_shadowban_alert",
    "sap_anomaly_detected",
]
