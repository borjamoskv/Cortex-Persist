"""Google One Tools — Integration for CORTEX ADK agents.

Provides tools to monitor storage, sync with NotebookLM sources,
and manage backups in Google Drive (Google One).
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cortex.cli.notebooklm_data import _detect_cloud_sync

logger = logging.getLogger("cortex.extensions.adk.goog_tools")


def goog_quota() -> dict[str, Any]:
    """
    Check the storage quota and availability of the Google One (Drive) sync folder.

    Returns:
        A dict with total, used, and free space in the Drive mount.
    """
    detected = _detect_cloud_sync()
    if not detected:
        return {"status": "error", "message": "Google Drive sync folder not detected."}

    path, provider = detected
    try:
        usage = shutil.disk_usage(path.parent)  # Check parent mount
        return {
            "status": "success",
            "provider": provider,
            "path": str(path),
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round((usage.used / usage.total) * 100, 1),
        }
    except OSError as e:
        return {"status": "error", "message": f"Could not check quota: {e}"}


def goog_sync_notebooklm(mode: str = "both", tenant_id: str = "default") -> dict[str, Any]:
    """
    Trigger a synchronization of CORTEX memory to NotebookLM sources in Google Drive.

    Args:
        mode: 'digest', 'domains', or 'both'.

    Returns:
        Status of the synchronization.
    """
    if mode not in {"digest", "domains", "both"}:
        return {"status": "error", "message": "Invalid mode. Use digest, domains, or both."}

    try:
        cmd = ["cortex", "notebooklm", "sync", "--mode", mode, "--tenant-id", tenant_id]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "NotebookLM sync completed successfully.",
                "output": result.stdout.strip(),
            }
        else:
            return {
                "status": "error",
                "message": "Sync command failed.",
                "stderr": result.stderr.strip(),
            }
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        return {"status": "error", "message": f"Sync process failed: {e}"}


def goog_backup_cortex() -> dict[str, Any]:
    """
    Create a backup of the CORTEX database and upload it to the Google Drive folder.

    Returns:
        Status of the backup operation.
    """
    from datetime import datetime, timezone

    if os.environ.get("CORTEX_ALLOW_FULL_DB_CLOUD_BACKUP") != "1":
        return {
            "status": "error",
            "message": (
                "Full database cloud backup is disabled by default. "
                "Set CORTEX_ALLOW_FULL_DB_CLOUD_BACKUP=1 outside the agent tool call."
            ),
        }

    detected = _detect_cloud_sync()
    if not detected:
        return {"status": "error", "message": "Google Drive sync folder not detected."}

    target_dir, _ = detected
    backup_dir = target_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    db_path = Path("~/.cortex/cortex.db").expanduser()
    if not db_path.exists():
        return {"status": "error", "message": f"Source DB not found at {db_path}"}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_name = f"cortex_sovereign_backup_{ts}.db"
    dest_path = backup_dir / dest_name

    try:
        # Use shutil.copy2 to preserve metadata
        shutil.copy2(db_path, dest_path)

        # Also backup context snapshot if it exists
        snapshot_path = Path("~/.cortex/context-snapshot.md").expanduser()
        if snapshot_path.exists():
            shutil.copy2(snapshot_path, backup_dir / f"context-snapshot_{ts}.md")

        return {
            "status": "success",
            "message": f"Sovereign backup created: {dest_name}",
            "path": str(dest_path),
            "size_mb": round(os.path.getsize(dest_path) / (1024**2), 2),
        }
    except OSError as e:
        return {"status": "error", "message": f"Backup failed: {e}"}


# List of all Google One tools for easy registration
GOOGLE_ONE_TOOLS = [goog_quota, goog_sync_notebooklm, goog_backup_cortex]
