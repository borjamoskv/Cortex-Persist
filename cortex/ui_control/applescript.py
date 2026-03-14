from __future__ import annotations

import asyncio
import logging

from cortex.ui_control.models import (
    AppleScriptExecutionError,
    AppNotRunningError,
    UIElementNotFoundError,
)

logger = logging.getLogger("cortex.ui_control")


async def run_applescript(
    script: str,
    require_success: bool = True,
    timeout: float = 30.0,
) -> str | None:
    """
    Ejecuta un AppleScript de forma asíncrona vía osascript.

    Args:
        script: El script AppleScript a ejecutar.
        require_success: Si True, lanza excepciones en caso de fallo.
        timeout: Tiempo máximo en segundos antes de matar el proceso.

    Returns:
        Output estándar del script, o None si falló (y require_success=False).

    Raises:
        AppNotRunningError: Si la app objetivo no está en ejecución.
        UIElementNotFoundError: Si no se encontró el elemento UI solicitado.
        AppleScriptExecutionError: Para otros errores genéricos de ejecución.
        TimeoutError: Si el script excede el timeout.
    """
    logger.debug("Ejecutando AppleScript:\n%s", script)

    process = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        if not require_success:
            logger.warning("AppleScript timeout tras %.1fs", timeout)
            return None
        raise TimeoutError(f"AppleScript excedió timeout de {timeout}s")

    decoded_out = stdout.decode("utf-8").strip() if stdout else ""
    decoded_err = stderr.decode("utf-8").strip() if stderr else ""

    if process.returncode != 0:
        if not require_success:
            logger.warning(
                "AppleScript falló (Exit %s): %s", process.returncode, decoded_err
            )
            return None

        error_lower = decoded_err.lower()
        if "is not running" in error_lower or "application isn't running" in error_lower:
            raise AppNotRunningError(
                f"App objetivo no está en ejecución: {decoded_err}"
            )

        if (
            "can't get window" in error_lower
            or "can't get menu" in error_lower
            or "can't get UI element" in error_lower
        ):
            raise UIElementNotFoundError(
                f"No se encontró el elemento UI: {decoded_err}"
            )

        raise AppleScriptExecutionError(
            "Fallo al ejecutar AppleScript",
            process.returncode or -1,
            decoded_err,
        )

    return decoded_out


async def is_app_running(app_name: str) -> bool:
    """Verifica si una aplicación está actualmente en ejecución."""
    script = f"""
    tell application "System Events"
        return (name of processes) contains "{app_name}"
    end tell
    """
    result = await run_applescript(script, require_success=False)
    return result == "true"


async def get_frontmost_app() -> str | None:
    """Devuelve el nombre de la aplicación en primer plano."""
    script = """
    tell application "System Events"
        set frontApp to first process whose frontmost is true
        return name of frontApp
    end tell
    """
    return await run_applescript(script, require_success=False)


async def set_clipboard(text: str) -> None:
    """Escribe texto al clipboard del sistema."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'set the clipboard to "{escaped}"'
    await run_applescript(script)


async def get_clipboard() -> str | None:
    """Lee el contenido actual del clipboard del sistema."""
    script = "return (the clipboard as text)"
    return await run_applescript(script, require_success=False)
