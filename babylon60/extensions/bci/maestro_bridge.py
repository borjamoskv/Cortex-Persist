# [C5-REAL] Exergy-Maximized
import asyncio
import inspect
import json
import logging
from typing import Any

from babylon60.extensions.ui_control.maestro import MaestroUI
from babylon60.extensions.ui_control.models import AppTarget, Point

logger = logging.getLogger("cortex.bci.maestro_bridge")


class BCIMaestroBridge:
    """
    Bridge that connects BCI Daemon intents to MaestroUI actions.
    """

    def __init__(self, maestro: MaestroUI | None = None) -> None:
        self.maestro = maestro or MaestroUI()

    async def handle_desktop_action(self, instruction: str, payload: str | bytes) -> Any:
        """
        Processes a desktop action from the BCI daemon and executes it on MaestroUI.

        Args:
            instruction: The MaestroUI method name (e.g. 'activate_app', 'inject_keystroke')
            payload: JSON string containing the arguments for the action.
        """
        logger.info(f"[BCI-Bridge] Resolving desktop action: {instruction}")

        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            args = json.loads(payload) if payload else {}
        except Exception as e:
            logger.error(f"[BCI-Bridge] Invalid JSON payload: {e}")
            return {"success": False, "error": f"Invalid JSON payload: {e}"}

        if not hasattr(self.maestro, instruction):
            err = f"MaestroUI has no attribute '{instruction}'"
            logger.error(f"[BCI-Bridge] {err}")
            return {"success": False, "error": err}

        method = getattr(self.maestro, instruction)

        # Map 'app' or 'app_name' to target AppTarget if the method expects one
        app_name = args.get("app") or args.get("app_name") or args.get("target")
        if app_name and isinstance(app_name, str):
            args["target"] = AppTarget(name=app_name)
            # Remove keys that might conflict
            args.pop("app", None)
            args.pop("app_name", None)

        # Map x, y to Point if needed
        if "x" in args and "y" in args:
            args["point"] = Point(x=int(args["x"]), y=int(args["y"]))
            args.pop("x", None)
            args.pop("y", None)

        try:
            # Handle if method is a coroutine or normal function
            if inspect.iscoroutinefunction(method):
                result = await method(**args)
            elif callable(method):
                # Check if it returns a coroutine (e.g. wrapped in lambda)
                res = method(**args)
                if asyncio.iscoroutine(res) or asyncio.isfuture(res):
                    result = await res
                else:
                    result = res
            else:
                result = method

            logger.info(f"[BCI-Bridge] Execution result of {instruction}: {result}")
            return result
        except Exception as e:
            logger.error(f"[BCI-Bridge] Error executing {instruction}: {e}")
            return {"success": False, "error": str(e)}


def get_bci_maestro_handlers(maestro: MaestroUI | None = None) -> dict[int, Any]:
    """
    Returns the action handlers mapping for the BCI Daemon to handle DESKTOP_ACTION.
    """
    bridge = BCIMaestroBridge(maestro)
    return {
        5: bridge.handle_desktop_action  # 5: DESKTOP_ACTION
    }
