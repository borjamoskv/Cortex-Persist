import asyncio
import logging

from cortex.ui_control.models import (
    AppleScriptExecutionError,
    AppNotRunningError,
    UIElementNotFoundError,
)

logger = logging.getLogger("cortex.ui_control")


async def run_applescript(script: str, require_success: bool = True) -> str | None:
    """
    Executes an AppleScript asynchronously using osascript.

    Args:
        script: The raw AppleScript string to execute.
        require_success: If True, raises exceptions on failure. If False, returns None.

    Returns:
        The stripped standard output of the script, or None if it failed (and require_success=False).

    Raises:
        AppNotRunningError: If the script fails because an app was not running.
        UIElementNotFoundError: If a targeted UI element was not found.
        AppleScriptExecutionError: For other generic execution errors.
    """
    logger.debug(f"Executing AppleScript:\n{script}")

    process = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    decoded_out = stdout.decode("utf-8").strip() if stdout else ""
    decoded_err = stderr.decode("utf-8").strip() if stderr else ""

    if process.returncode != 0:
        if not require_success:
            logger.warning("AppleScript failed (Exit %s): %s", process.returncode, decoded_err)
            return None

        error_lower = decoded_err.lower()
        if "is not running" in error_lower or "application isn’t running" in error_lower:
            raise AppNotRunningError(f"Target application is not running: {decoded_err}")

        if "can’t get window" in error_lower or "can’t get menu" in error_lower or "can’t get UI element" in error_lower:
             raise UIElementNotFoundError(f"Failed to locate UI element: {decoded_err}")

        raise AppleScriptExecutionError("Failed to execute AppleScript", process.returncode or -1, decoded_err)

    return decoded_out


async def is_app_running(app_name: str) -> bool:
    """Checks if a specified application is currently running."""
    script = f"""
    tell application "System Events"
        return (name of processes) contains "{app_name}"
    end tell
    """
    result = await run_applescript(script, require_success=False)
    # AppleScript returns boolean strings like "true" or "false"
    return result == "true"
