"""Cross-platform utilities for CORTEX.

Centralized helpers for OS detection, path resolution, and
platform-specific executable lookup. Replaces all hardcoded
paths and platform-specific assumptions scattered across the codebase.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = [
    "get_cortex_dir",
    "get_python_executable",
    "get_service_dir",
    "is_linux",
    "is_macos",
    "is_windows",
    "platform_name",
    "tail_file_command",
]

# ─── Platform Detection ──────────────────────────────────────────────


def is_macos() -> bool:
    """True if running on macOS (Darwin)."""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """True if running on Linux."""
    return sys.platform.startswith("linux")


def is_windows() -> bool:
    """True if running on Windows."""
    return sys.platform == "win32"


def platform_name() -> str:
    """Human-readable platform name: 'macOS', 'Linux', or 'Windows'."""
    if is_macos():
        return "macOS"
    if is_linux():
        return "Linux"
    if is_windows():
        return "Windows"
    return sys.platform


# ─── Path Resolution ─────────────────────────────────────────────────


def get_cortex_dir() -> Path:
    """Return the CORTEX data directory.

    - macOS / Linux: ``~/.cortex``
    - Windows: ``%APPDATA%/cortex``
    """
    if is_windows():
        appdata = Path.home() / "AppData" / "Roaming" / "cortex"
    else:
        appdata = Path.home() / ".cortex"
    appdata.mkdir(parents=True, exist_ok=True)
    return appdata


def get_python_executable() -> str:
    """Return the current Python interpreter path.

    This replaces all hardcoded ``/Users/.../venv/bin/python``
    references, making the code work regardless of OS or venv location.
    """
    return sys.executable


def get_service_dir() -> Path | None:
    """Return the platform-specific user service directory.

    - macOS: ``~/Library/LaunchAgents``
    - Linux: ``~/.config/systemd/user``
    - Windows: returns None (uses Task Scheduler API, not a directory)
    """
    if is_macos():
        return Path.home() / "Library" / "LaunchAgents"
    if is_linux():
        return Path.home() / ".config" / "systemd" / "user"
    return None


# ─── Log File Viewer ─────────────────────────────────────────────────


def tail_file_command(path: str) -> list[str]:
    """Return the command to follow (tail) a log file.

    - Unix:    ``['tail', '-f', path]``
    - Windows: ``['powershell', 'Get-Content', path, '-Wait']``
    """
    if is_windows():
        return ["powershell", "Get-Content", path, "-Wait"]
    return ["tail", "-f", path]
