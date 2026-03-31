"""
macOS launchd Integration for CORTEX-Persist Daemon.

Generates local LaunchAgents plist, loads them via launchctl.
"""

import subprocess
from pathlib import Path

import click

PLIST_NAME = "com.cortexpersist.moskv.plist"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME
LOG_DIR = Path.home() / ".cortex" / "logs"
STDOUT_LOG = LOG_DIR / "daemon.out"
STDERR_LOG = LOG_DIR / "daemon.err"


def _get_project_root() -> Path:
    """Resolve project root based on this file's location."""
    # cortex/extensions/daemon/launcher_mac.py -> Root
    return Path(__file__).resolve().parent.parent.parent.parent


def get_plist_content() -> str:
    root = _get_project_root()
    # Locate Python in standard `uv` venv setup
    venv_python = root / ".venv" / "bin" / "python"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cortexpersist.moskv</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-l</string>
        <string>-c</string>
        <string>exec "{venv_python}" -m cortex.cli.__main__ daemons run</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{root}</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>CORTEX_DAEMON_MODE</key>
        <string>1</string>
    </dict>
    <key>StandardOutPath</key>
    <string>{STDOUT_LOG}</string>
    <key>StandardErrorPath</key>
    <string>{STDERR_LOG}</string>
</dict>
</plist>"""


class MacLaunchDaemon:
    @staticmethod
    def is_installed() -> bool:
        return PLIST_PATH.exists()

    @staticmethod
    def install():
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

        plist_data = get_plist_content()
        with open(PLIST_PATH, "w") as f:
            f.write(plist_data)

        click.secho(f"Plist written to {PLIST_PATH}", fg="green")

        # Reload plist into launchd
        MacLaunchDaemon.unload(silent=True)
        subprocess.run(["launchctl", "load", "-w", str(PLIST_PATH)], check=True)
        click.secho("Daemon loaded into macOS launchd.", fg="cyan")

        # TCC Diagnostic
        from cortex.extensions.daemon.tcc_helper import check_folder_access

        if not check_folder_access(Path.home() / "Desktop"):
            click.secho(
                "\n[!] TCC WARNING: Daemon is blocked from accessing folders.",
                fg="yellow",
                bold=True,
            )
            click.echo("To fix this, run: cortex daemons authorize")

    @staticmethod
    def uninstall():
        if not MacLaunchDaemon.is_installed():
            click.secho("Daemon not installed.", fg="yellow")
            return

        MacLaunchDaemon.unload(silent=True)
        PLIST_PATH.unlink()
        click.secho("Daemon uninstalled.", fg="yellow")

    @staticmethod
    def start():
        subprocess.run(["launchctl", "start", "com.cortexpersist.moskv"], check=True)

    @staticmethod
    def stop():
        subprocess.run(["launchctl", "stop", "com.cortexpersist.moskv"], check=True)

    @staticmethod
    def unload(silent: bool = False):
        res = subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
        if not silent and res.returncode != 0:
            click.echo(res.stderr.decode("utf-8"))
