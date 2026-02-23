"""Platform-specific daemon install/uninstall.

Extracted from daemon_cli.py to keep file size under 300 LOC.
Supports macOS (launchd), Linux (systemd), and Windows (Task Scheduler).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from rich.console import Console

from cortex.daemon import BUNDLE_ID
from cortex.sys_platform import get_service_dir

__all__ = [
    "install_macos",
    "install_linux",
    "install_windows",
    "uninstall_macos",
    "uninstall_linux",
    "uninstall_windows",
]

console = Console()

PLIST_SOURCE = Path(__file__).parent.parent / "launchd" / f"{BUNDLE_ID}.plist"


def _get_plist_dest() -> Path:
    """macOS launchd plist destination."""
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _get_systemd_unit() -> Path:
    """Linux systemd user unit destination."""
    svc_dir = get_service_dir()
    assert svc_dir is not None  # noqa: S101
    return svc_dir / f"{BUNDLE_ID}.service"


# ─── macOS ──────────────────────────────────────────────────────────


def install_macos() -> None:
    if not PLIST_SOURCE.exists():
        console.print(f"[red]❌ Plist not found: {PLIST_SOURCE}[/]")
        sys.exit(1)
    dest = _get_plist_dest()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLIST_SOURCE, dest)
    console.print(f"[green]✅ Installed:[/] {dest}")
    import subprocess

    subprocess.run(["launchctl", "load", str(dest)], check=False)
    console.print(f"[green]✅ Loaded:[/] {BUNDLE_ID}")
    console.print("[dim]   Daemon will run every 5 minutes and on login.[/]")


def uninstall_macos() -> None:
    import subprocess

    dest = _get_plist_dest()
    if dest.exists():
        subprocess.run(["launchctl", "unload", str(dest)], check=False)
        dest.unlink()
        console.print(f"[green]✅ Removed:[/] {BUNDLE_ID}")
    else:
        console.print("[yellow]No launchd agent installed.[/]")


# ─── Linux ──────────────────────────────────────────────────────────


def install_linux() -> None:
    unit_path = _get_systemd_unit()
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable
    unit_content = f"""[Unit]
Description=MOSKV-1 CORTEX Daemon
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m cortex.daemon_cli start
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
"""
    unit_path.write_text(unit_content)
    console.print(f"[green]✅ Installed:[/] {unit_path}")
    import subprocess

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", BUNDLE_ID], check=False)
    console.print(f"[green]✅ Enabled:[/] {BUNDLE_ID}")
    console.print("[dim]   Daemon will run automatically on login.[/]")


def uninstall_linux() -> None:
    import subprocess

    unit_path = _get_systemd_unit()
    if unit_path.exists():
        subprocess.run(["systemctl", "--user", "disable", "--now", BUNDLE_ID], check=False)
        unit_path.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        console.print(f"[green]✅ Removed:[/] {BUNDLE_ID}")
    else:
        console.print("[yellow]No systemd unit installed.[/]")


# ─── Windows ────────────────────────────────────────────────────────


def install_windows() -> None:
    import subprocess

    python_path = sys.executable
    task_name = BUNDLE_ID.replace(".", "_")
    cmd = (
        f'schtasks /Create /SC ONLOGON /TN "{task_name}" '
        f'/TR ""{python_path}" -m cortex.daemon_cli start" '
        f"/F /RL LIMITED"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        console.print(f"[green]✅ Installed:[/] Task Scheduler → {task_name}")
        console.print("[dim]   Daemon will run automatically on login.[/]")
    else:
        console.print(f"[red]❌ Failed:[/] {result.stderr.strip()}")


def uninstall_windows() -> None:
    import subprocess

    task_name = BUNDLE_ID.replace(".", "_")
    result = subprocess.run(
        f'schtasks /Delete /TN "{task_name}" /F',
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        console.print(f"[green]✅ Removed:[/] {task_name}")
    else:
        console.print("[yellow]No scheduled task found.[/]")
