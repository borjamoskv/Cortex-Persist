# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: scarcity-governor
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
C5-REAL: "M\xD6BIUS OS Scarcity Governor"
"""


import json
import sys
from datetime import datetime, timezone

import psutil

# C5-REAL Thresholds
MIN_MEMORY_AVAILABLE_GB = 4.0
MAX_CPU_PERCENT = 85.0


def get_system_telemetry():
    """Extract thermodynamic metrics from local host."""
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cpu_percent": cpu,
        "memory_available_gb": mem.available / (1024**3),
        "memory_percent": mem.percent,
    }


def evaluate_mitosis_scarcity(telemetry):
    """Determine if local environment can support new subagent mitosis."""
    if telemetry["memory_available_gb"] < MIN_MEMORY_AVAILABLE_GB:
        return False, "SCARCITY_LOCK: Insufficient memory available (<4GB)."
    if telemetry["cpu_percent"] > MAX_CPU_PERCENT:
        return False, "SCARCITY_LOCK: CPU pressure too high (>85%)."
    return True, "EXERGY_CLEARED: Environment stable for mitosis."


def main():
    telemetry = get_system_telemetry()
    cleared, reason = evaluate_mitosis_scarcity(telemetry)

    payload = {
        "sys_id": "SCARCITY_GOVERNOR_OMEGA",
        "state": "C5-REAL",
        "telemetry": telemetry,
        "mitosis_approved": cleared,
        "reason": reason,
    }

    print(json.dumps(payload, indent=2))

    if not cleared:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
