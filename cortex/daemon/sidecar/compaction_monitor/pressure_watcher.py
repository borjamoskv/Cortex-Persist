"""pressure_watcher.py

Async watcher that monitors cgroup v2 PSI (memory pressure) and triggers a
compaction job when the "some" pressure exceeds a configurable threshold.

The watcher reads the ``/sys/fs/cgroup/memory.pressure`` file (available on
Linux with cgroup v2). For macOS we simulate pressure by reading the system
memory stats via ``vm_stat`` as a fallback.
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable

import aiofiles

LOGGER = logging.getLogger(__name__)

# Default threshold for "some" pressure (percentage). Adjust via env var.
DEFAULT_THRESHOLD = float(os.getenv("PSI_PRESSURE_THRESHOLD", "70"))

# Path to the cgroup PSI file – may not exist on macOS.
CGROUP_PSI_PATH = "/sys/fs/cgroup/memory.pressure"


async def _read_cgroup_pressure() -> float:
    """Read the ``some`` pressure value from the cgroup PSI file.

    Returns the percentage (0‑100). If the file is missing, returns ``0``.
    """
    try:
        async with aiofiles.open(CGROUP_PSI_PATH) as f:
            content = await f.read()
        # Example line: "some 70/1000000 avg10=0.00 avg60=0.00 avg300=0.00 total=0"
        for part in content.split():
            if part.startswith("some"):
                # Format can be "some 70/1000000" – we take the first number.
                value = part.split()[1] if len(part.split()) > 1 else part.split("=")[1]
                percent = float(value.split("/")[0])
                return percent
    except Exception as exc:
        LOGGER.debug("cgroup PSI not available: %s", exc)
    return 0.0


async def _read_macos_pressure() -> float:
    """Fallback for macOS – estimate pressure using ``vm_stat``.

    This is a rough approximation: we consider the number of free pages vs.
    total pages and treat high usage as pressure.
    """
    try:
        proc = await asyncio.create_subprocess_shell(
            "vm_stat",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        lines = stdout.decode().splitlines()
        stats = {}
        for line in lines:
            if ":" in line:
                key, val = line.split(":")
                stats[key.strip()] = int(val.strip().strip(".").replace(".", ""))
        free = stats.get("Pages free", 0)
        active = stats.get("Pages active", 0)
        inactive = stats.get("Pages inactive", 0)
        total = free + active + inactive
        used_percent = 100.0 * (total - free) / total if total else 0.0
        return used_percent
    except Exception as exc:
        LOGGER.debug("macOS pressure estimation failed: %s", exc)
    return 0.0


async def start_pressure_watcher(compaction_callback: Callable[[any], Awaitable[None]]) -> None:
    """Continuously monitor memory pressure and invoke ``compaction_callback``.

    The callback receives a single argument – the current pressure percentage –
    but can ignore it. The watcher sleeps for a short interval (default 5 s) and
    re‑reads the pressure metric.
    """
    interval = int(os.getenv("PSI_WATCH_INTERVAL", "5"))
    threshold = float(os.getenv("PSI_PRESSURE_THRESHOLD", str(DEFAULT_THRESHOLD)))
    LOGGER.info("Starting pressure watcher (threshold=%s%%, interval=%ss)", threshold, interval)
    while True:
        # Choose platform‑specific source
        if os.path.exists(CGROUP_PSI_PATH):
            pressure = await _read_cgroup_pressure()
        else:
            pressure = await _read_macos_pressure()
        if pressure >= threshold:
            LOGGER.info(
                "Memory pressure %.1f%% exceeds threshold %.1f%% – triggering compaction",
                pressure,
                threshold,
            )
            try:
                await compaction_callback(pressure)
            except Exception as exc:
                LOGGER.exception("Compaction callback failed: %s", exc)
        await asyncio.sleep(interval)
