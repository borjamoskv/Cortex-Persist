"""VisionBridge — Agentic UI perception provider for the Swarm via Mac Omega."""

import logging
from typing import Any, Optional
from scripts.mac_control.cdp_engine import MacControlOmega

logger = logging.getLogger("cortex.swarm.vision")

class VisionBridge:
    """Connects Swarm agents to the macOS UI via CDP."""

    def __init__(self, target_pattern: str = "github.com"):
        self.target = target_pattern
        self.ctl = MacControlOmega()

    async def get_ui_context(self, selector: Optional[str] = None) -> dict[str, Any]:
        """Retrieve text or HTML context from the target UI tab."""
        connected = await self.ctl.connect(self.target)
        if not connected:
            return {"error": f"Could not connect to tab matching '{self.target}'"}

        try:
            if selector:
                content = await self.ctl.extract_selector(selector)
            else:
                content = await self.ctl.extract_page()

            return {
                "content": content[:2000] if content else "",
                "truncated": len(content or "") > 2000,
                "target": self.target
            }
        finally:
            await self.ctl.close()

    async def capture_evidence(self, filepath: str) -> bool:
        """Take a screenshot for mission evidence."""
        connected = await self.ctl.connect(self.target)
        if not connected:
            return False

        try:
            await self.ctl.screenshot(filepath)
            return True
        finally:
            await self.ctl.close()
