"""Cross-platform notifications for MOSKV-1 daemon.

Dispatches to the native notification system:
- macOS:   osascript (AppleScript)
- Linux:   notify-send (libnotify)
- Windows: PowerShell toast fallback
"""

from __future__ import annotations

import logging
import subprocess

from cortex.daemon.models import GhostAlert, MemoryAlert, SiteStatus
from cortex.platform import is_linux, is_macos, is_windows

logger = logging.getLogger("moskv-daemon")


class Notifier:
    """Platform-aware native notifications."""

    @staticmethod
    def notify(title: str, message: str, sound: str = "Submarine") -> bool:
        """Send a native notification. Returns True on success."""
        try:
            if is_macos():
                return Notifier._notify_macos(title, message, sound)
            if is_linux():
                return Notifier._notify_linux(title, message)
            if is_windows():
                return Notifier._notify_windows(title, message)
            # Fallback: just log
            logger.info("[Notification] %s: %s", title, message)
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Notification failed: %s", e)
            return False

    @staticmethod
    def _notify_macos(title: str, message: str, sound: str) -> bool:
        """macOS: osascript AppleScript notification."""
        # Escape double quotes in title/message
        safe_title = title.replace('"', '\\"')
        safe_msg = message.replace('"', '\\"')
        script = f'display notification "{safe_msg}" with title "{safe_title}" sound name "{sound}"'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return True

    @staticmethod
    def _notify_linux(title: str, message: str) -> bool:
        """Linux: notify-send (libnotify)."""
        subprocess.run(
            ["notify-send", "--urgency=normal", title, message],
            capture_output=True,
            timeout=5,
        )
        return True

    @staticmethod
    def _notify_windows(title: str, message: str) -> bool:
        """Windows: PowerShell toast notification."""
        # Escape single quotes for PowerShell
        safe_title = title.replace("'", "''")
        safe_msg = message.replace("'", "''")
        ps_script = (
            f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
            f"$balloon = New-Object System.Windows.Forms.NotifyIcon; "
            f"$balloon.Icon = [System.Drawing.SystemIcons]::Information; "
            f"$balloon.BalloonTipTitle = '{safe_title}'; "
            f"$balloon.BalloonTipText = '{safe_msg}'; "
            f"$balloon.Visible = $true; "
            f"$balloon.ShowBalloonTip(5000)"
        )
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=10,
        )
        return True

    @staticmethod
    def alert_site_down(site: SiteStatus) -> None:
        Notifier.notify(
            "⚠️ MOSKV-1 — Site Down",
            f"{site.url} is unreachable: {site.error or f'HTTP {site.status_code}'}",
            sound="Basso",
        )

    @staticmethod
    def alert_stale_project(ghost: GhostAlert) -> None:
        hours = int(ghost.hours_stale)
        Notifier.notify(
            "💤 MOSKV-1 — Proyecto Stale",
            f"{ghost.project} lleva {hours}h sin actividad",
        )

    @staticmethod
    def alert_memory_stale(alert: MemoryAlert) -> None:
        hours = int(alert.hours_stale)
        Notifier.notify(
            "🧠 MOSKV-1 — CORTEX Stale",
            f"{alert.file} sin actualizar ({hours}h). Ejecuta /memoria",
        )
