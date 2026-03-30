"""Maxwell Audit — Exergy Filtering for Red Team Swarm.

This module provides the audit interface for Maxwell's performance engine,
enforcing thermodynamic exergy filters on agentic outputs.
"""

from __future__ import annotations
from typing import Any
from cortex.utils.result import Ok, Err, Result
from cortex.daemon.maxwell import MaxwellDaemon

class ExergyAudit:
    """Audit interface for Maxwell's Exergy filtering."""
    
    def __init__(self, engine: Any):
        self.engine = engine
        self.daemon = MaxwellDaemon(engine)
        
    async def verify_exergy(self, payload: str) -> Result[bool, str]:
        """Verify the exergy of a payload before processing.
        
        Returns Ok(True) if exergy is sufficient, Err(reason) otherwise.
        """
        res = await self.daemon.intercept_bus_event(payload)
        if res.is_err():
            return Err(res.err())
        return Ok(True)
