"""FEP-Moravec Guard implementation (AX-037).

Enforces thermodynamic bounds for active inference. Silicon emulating biological intuition
causes Exergy Fraud.
"""

from typing import Any

import aiosqlite


class FEPMoravecGuard:
    """AX-037 Thermodynamic limits enforcer."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        requires_active_inference = bool(meta.get("requires_active_inference", False))
        biological_stakes = int(meta.get("biological_stakes", 0))

        if requires_active_inference or biological_stakes > 0:
            raise ValueError(
                "[AX-037] CortexHalt: Vector B (FEP Bound). Emular intuición biológica en "
                "silicio causa Fraude Exérgico."
            )
