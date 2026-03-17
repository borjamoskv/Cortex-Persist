"""Gidatu UI/Desktop Orchestration Handler.
Ω₃ (Byzantine Default): Enforces SafeZones and strict app-scoping.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.gateway import GatewayRequest

logger = logging.getLogger("cortex.gateway.gidatu")


class GidatuHandler:
    """Handles UI orchestration requests using the Gidatu skill."""

    def __init__(self):
        self._skill_path = Path("~/.gemini/antigravity/skills/Gidatu/scripts").expanduser()
        self._ensure_path()

    def _ensure_path(self):
        if str(self._skill_path) not in sys.path:
            sys.path.insert(0, str(self._skill_path))

    async def handle(self, req: "GatewayRequest") -> dict[str, Any]:
        """Process a Gidatu action request."""
        try:
            # Ghost checking
            pass
        except ImportError as e:
            raise ImportError(f"Gidatu skill scripts not found at {self._skill_path}") from e

        action = req.payload.get("action", "status")
        params = req.payload.get("params", {})
        timeout = float(req.payload.get("timeout", 5.0))
        app = req.payload.get("app")

        # logic for actions - Wrap in to_thread for non-blocking IO
        import asyncio

        return await asyncio.to_thread(self._sync_handle, action, params, timeout, app)

    def _sync_handle(
        self, action: str, params: dict, timeout: float, app: Optional[str]
    ) -> dict[str, Any]:
        from ghost_chain import Ghost
        from ghost_platform import platform_info
        from ghost_vlm import find_text_on_screen

        with Ghost(app=app) as g:
            # Native SafeZone enforcement (Ω₃)
            if "safe_zone" in params:
                from ghost_guard import SafeZone

                sz = params["safe_zone"]
                g.guard_zone(SafeZone(sz["x"], sz["y"], sz["w"], sz["h"]))

            if action == "click":
                return self._do_click(g, params)

            if action == "click_text":
                return self._do_click_text(g, params, timeout)

            if action == "type":
                g.type(params["text"])
                return {"action": "type", "success": True}

            if action == "hotkey":
                g.hotkey(*params["keys"])
                return {"action": "hotkey", "keys": params["keys"]}

            if action == "screenshot":
                path = params.get("path", f"/tmp/shot_{int(time.time())}.png")
                g.screenshot(path)
                return {"action": "screenshot", "path": path}

            if action == "vlm":
                text = params.get("text")
                match = find_text_on_screen(text) if text else None
                return {"action": "vlm", "found": bool(match), "match": match}

            if action == "status":
                return {"status": "ready", "platform": platform_info()}

            raise ValueError(f"Unknown Gidatu action: {action}")

    def _do_click(self, g, params):
        x, y = params.get("x"), params.get("y")
        if x is None or y is None:
            raise ValueError("params.x and params.y are required for click")
        g.click(x, y)
        return {"action": "click", "coords": [x, y]}

    def _do_click_text(self, g, params, timeout):
        from ghost_resilience import wait_until
        from ghost_vlm import find_text_on_screen

        text = params.get("text")
        if not text:
            raise ValueError("params.text is required for click_text")
        found = wait_until(lambda: find_text_on_screen(text), timeout=timeout)
        if not found:
            raise RuntimeError(f"Text '{text}' not found on screen")
        g.click(found["x"], found["y"])
        return {"action": "click_text", "text": text, "coords": [found["x"], found["y"]]}
