from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def get_orphaned_browsers():
    """Identify orphaned ms-playwright-go processes."""
    try:
        # /bin/ps aux | grep ms-playwright-go
        ps = subprocess.check_output(["/bin/ps", "aux"], text=True)
        orphans = [
            line for line in ps.split("\n") if "ms-playwright-go" in line and "grep" not in line
        ]
        return orphans
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Failed to get orphaned browsers: %s", e)
        return []


def get_snapshot_age():
    """Return the age of the CORTEX snapshot in minutes."""
    from cortex.core.paths import CORTEX_DIR

    snapshot_path = CORTEX_DIR / "context-snapshot.md"
    if not snapshot_path.exists():
        return float("inf")
    mtime = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mtime).total_seconds() / 60
    return age


def check_system_health():
    """Full hygiene check."""
    report = {
        "orphans": len(get_orphaned_browsers()),
        "snapshot_age_min": get_snapshot_age(),
        "load_average": os.getloadavg(),
    }
    return report


if __name__ == "__main__":
    health = check_system_health()
    sys.stdout.write("Hygiene Status:\n")
    sys.stdout.write(f" - Orphaned Browsers: {health['orphans']}\n")
    sys.stdout.write(f" - Snapshot Age: {health['snapshot_age_min']:.1f} min\n")
    sys.stdout.write(f" - Load Average: {health['load_average']}\n")
