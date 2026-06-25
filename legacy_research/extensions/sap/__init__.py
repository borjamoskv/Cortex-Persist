# [C5-REAL] Exergy-Maximized
"""SAP OData Integration.

Bidirectional sync between SAP business objects and CORTEX facts.
Enables AI agents to read/write SAP entities with full ledger traceability.
"""

from legacy_research.extensions.sap.client import (
    SAPAuthError,
    SAPClient,
    SAPConfig,
    SAPConnectionError,
    SAPEntityError,
)
from legacy_research.extensions.sap.mapper import SAPMapper, SyncDiff
from legacy_research.extensions.sap.sync import SAPSync, SAPSyncResult

__all__ = [
    "SAPAuthError",
    "SAPClient",
    "SAPConfig",
    "SAPConnectionError",
    "SAPEntityError",
    "SAPMapper",
    "SAPSync",
    "SAPSyncResult",
    "SyncDiff",
]
