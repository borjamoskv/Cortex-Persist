"""Mac-Maestro-Ω — AppleScript wrappers (Vector A)."""

from __future__ import annotations

import logging
import re
import subprocess

logger = logging.getLogger("mac_maestro.applescript")

# Translation table for O(1) character escape
_ESCAPE_TABLE = str.maketrans({
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
})

# Regex to strip control characters (except those handled above)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class AppleScriptError(Exception):
    pass


def sanitize_applescript_string(value: object) -> str:
    """Sanitize a value for safe interpolation into AppleScript.

    Escapes backslashes, double quotes, newlines, tabs, carriage returns.
    Strips null bytes and other control characters.
    """
    s = str(value)
    s = s.translate(_ESCAPE_TABLE)
    s = _CTRL_RE.sub("", s)
    return s


def run_applescript(script: str) -> str:
    """Execute an AppleScript string via osascript."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise AppleScriptError(
                f"osascript error (rc={result.returncode}): "
                f"{result.stderr.strip()}"
            )
        return result.stdout.strip()
    except subprocess.TimeoutExpired as exc:
        raise AppleScriptError("AppleScript timed out after 30s") from exc


def activate_app_by_name(app_name: str) -> str:
    """Activate an application by name."""
    safe_name = sanitize_applescript_string(app_name)
    return run_applescript(
        f'tell application "{safe_name}" to activate'
    )


def open_url_in_safari(url: str) -> str:
    """Open a URL in Safari."""
    safe_url = sanitize_applescript_string(url)
    return run_applescript(
        f'tell application "Safari" to open location "{safe_url}"'
    )
