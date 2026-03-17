"""
CORTEX MEJORAlo — Mac Control Module.

macOS system telemetry scanner following mac-maestro-omega Semantic > Spatial ladder.

Vector priority:
  1. Native macOS CLI (vm_stat, sysctl, ioreg, osascript) — no external deps
  2. Structured parsing with safe fallbacks per field
  3. Graceful degradation on non-darwin: returns MacSnapshot(platform="unsupported")

Exposes:
  mac_system_snapshot() -> MacSnapshot
  score_mac_control(snapshot) -> tuple[int, list[str]]
"""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

from cortex.extensions.mejoralo.constants import (
    MAC_AX_PENALTY,
    MAC_MEMORY_PRESSURE_WARN,
    MAC_PROCESS_ENTROPY_LIMIT,
    MAC_PROCESS_PENALTY_PER_10,
    MAC_THERMAL_OK,
)
from cortex.extensions.mejoralo.models import MacSnapshot

__all__ = ["mac_system_snapshot", "score_mac_control"]

logger = logging.getLogger("cortex.extensions.mejoralo.mac_control")

# ── Internal helpers ──────────────────────────────────────────────────


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    """Execute a shell command and return stdout as string. Never raises."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("mac_control._run failed for %s: %s", cmd[0], exc)
        return ""


def _parse_vm_stat() -> str:
    """
    Return memory pressure level: 'ok' | 'warn' | 'critical'.

    Uses: sysctl vm.memory_pressure (0=ok, 1=warn, 2=critical)
    Fallback: parse vm_stat page-outs as heuristic.
    """
    raw = _run(["sysctl", "-n", "vm.memory_pressure"])
    if raw in ("0", "1", "2"):
        level_map = {"0": "ok", "1": "warn", "2": "critical"}
        return level_map[raw]

    # Fallback: inspect vm_stat page-out count
    vm_stat_out = _run(["vm_stat"])
    po_line = next((line for line in vm_stat_out.splitlines() if "pageouts" in line.lower()), "")
    if po_line:
        try:
            count = int(po_line.split(":")[-1].strip().rstrip("."))
            if count > 10_000:
                return "warn"
        except (ValueError, IndexError):
            pass
    return "ok"


def _parse_cpu_percent() -> float:
    """
    Return CPU utilisation % via sysctl + top -l 1 idle reading.
    Fallback: 0.0 if parsing fails.
    """
    raw = _run(["top", "-l", "1", "-n", "0", "-s", "0"])
    for line in raw.splitlines():
        if "CPU usage" in line or "cpu usage" in line.lower():
            # e.g. "CPU usage: 8.32% user, 12.44% sys, 79.23% idle"
            try:
                for part in line.split(","):
                    if "idle" in part.lower():
                        idle = float(part.strip().split()[0].rstrip("%"))
                        return round(100.0 - idle, 2)
            except (ValueError, IndexError):
                break
    return 0.0


def _parse_thermal_state() -> str:
    """
    Return thermal state: 'Nominal' | 'Fair' | 'Serious' | 'Critical'.
    Uses ioreg IOPlatformExpertDevice.
    Fallback: 'Nominal' (optimistic — not penalise without evidence).
    """
    raw = _run(["ioreg", "-r", "-c", "IOPlatformExpertDevice"])
    for line in raw.splitlines():
        if "thermal" in line.lower():
            for state in ("Nominal", "Fair", "Serious", "Critical"):
                if state in line:
                    return state
    # macOS 12+: pmset -g therm
    therm = _run(["pmset", "-g", "therm"])
    if "CPU_Speed_Limit" in therm:
        for line in therm.splitlines():
            if "CPU_Speed_Limit" in line:
                try:
                    limit = int(line.split("=")[-1].strip())
                    if limit < 80:
                        return "Serious"
                    if limit < 95:
                        return "Fair"
                except (ValueError, IndexError):
                    pass
    return "Nominal"


def _parse_process_count() -> int:
    """Return total running process count via ps."""
    raw = _run(["ps", "-A", "-o", "pid"])
    lines = [line for line in raw.splitlines() if line.strip() and line.strip() != "PID"]
    return len(lines)


def _parse_ax_trusted() -> bool:
    """
    Return True if this process has Accessibility trust (AXIsProcessTrusted).
    Uses osascript: if it can query System Events it is trusted.
    """
    script = 'tell application "System Events" to get name of first process'
    raw = _run(["osascript", "-e", script], timeout=3.0)
    return bool(raw) and "not allowed" not in raw.lower()


def _parse_gpu_active() -> bool:
    """
    Return True if discrete GPU is active (Metal + Window Server load).
    Uses ioreg IOAccelerator for discrete GPU presence.
    """
    raw = _run(["ioreg", "-r", "-c", "IOPCIDevice"])
    return "AMD" in raw or "NVIDIA" in raw or "Apple M" in raw


# ── Public API ────────────────────────────────────────────────────────


def mac_system_snapshot() -> MacSnapshot:
    """
    Capture a live macOS system snapshot.

    On non-darwin platforms returns MacSnapshot(platform="unsupported")
    so callers can gracefully skip scoring.
    """
    if sys.platform != "darwin":
        return MacSnapshot(
            platform="unsupported",
            cpu_percent=0.0,
            memory_pressure="ok",
            thermal_state=MAC_THERMAL_OK,
            process_count=0,
            ax_trusted=False,
            gpu_active=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    cpu = _parse_cpu_percent()
    mem_pressure = _parse_vm_stat()
    thermal = _parse_thermal_state()
    proc_count = _parse_process_count()
    ax = _parse_ax_trusted()
    gpu = _parse_gpu_active()

    snapshot = MacSnapshot(
        platform="darwin",
        cpu_percent=cpu,
        memory_pressure=mem_pressure,
        thermal_state=thermal,
        process_count=proc_count,
        ax_trusted=ax,
        gpu_active=gpu,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.debug("MacSnapshot: %s", snapshot)
    return snapshot


def score_mac_control(snapshot: MacSnapshot) -> tuple[int, list[str]]:
    """
    Score macOS system health 0-100 with structured findings.

    Returns:
        (score, findings) — score=-1 signals unsupported platform (no penalty).
    """
    if snapshot.platform == "unsupported":
        return -1, []

    findings: list[str] = []
    score = 100

    # ── Accessibility Trust ───────────────────────────────────────────
    if not snapshot.ax_trusted:
        score -= MAC_AX_PENALTY
        findings.append(
            f"mac_control: AX trust not granted — automation integrity compromised "
            f"(penalty -{MAC_AX_PENALTY}). "
            "Grant access via System Settings → Privacy & Security → Accessibility."
        )

    # ── Memory Pressure ───────────────────────────────────────────────
    if snapshot.memory_pressure == MAC_MEMORY_PRESSURE_WARN:
        score -= 20
        findings.append(
            "mac_control: Memory pressure WARN — system under memory stress. "
            "Close unused applications or investigate memory leaks."
        )
    elif snapshot.memory_pressure == "critical":
        score -= 40
        findings.append(
            "mac_control: Memory pressure CRITICAL — severe memory degradation. "
            "Immediate intervention required."
        )

    # ── Thermal State ─────────────────────────────────────────────────
    thermal_penalties: dict[str, tuple[int, str]] = {
        "Fair": (10, "Fair thermal state — minor throttling active."),
        "Serious": (25, "Serious thermal state — significant CPU throttling."),
        "Critical": (40, "Critical thermal state — system in emergency thermal protection."),
    }
    if snapshot.thermal_state in thermal_penalties:
        penalty, msg = thermal_penalties[snapshot.thermal_state]
        score -= penalty
        findings.append(f"mac_control: {msg}")

    # ── Process Entropy ───────────────────────────────────────────────
    if snapshot.process_count > MAC_PROCESS_ENTROPY_LIMIT:
        excess = snapshot.process_count - MAC_PROCESS_ENTROPY_LIMIT
        penalty = min(30, (excess // 10) * MAC_PROCESS_PENALTY_PER_10)
        score -= penalty
        findings.append(
            f"mac_control: Process entropy high ({snapshot.process_count} procs, "
            f"limit {MAC_PROCESS_ENTROPY_LIMIT}) — daemon sprawl risk (penalty -{penalty})."
        )

    # ── CPU Spike ─────────────────────────────────────────────────────
    if snapshot.cpu_percent > 90.0:
        cpu_penalty = min(15, int((snapshot.cpu_percent - 90) * 1.5))
        score -= cpu_penalty
        findings.append(
            f"mac_control: CPU at {snapshot.cpu_percent:.1f}% — system saturation "
            f"(penalty -{cpu_penalty})."
        )

    return max(0, score), findings


def mac_control_dimension_kwargs(snapshot: MacSnapshot | None = None) -> dict[str, Any]:
    """
    Build kwargs for DimensionResult from a MacSnapshot.

    Convenience wrapper for scan.py injection.
    """
    s = snapshot if snapshot is not None else mac_system_snapshot()
    score, findings = score_mac_control(s)
    return {
        "name": "Control macOS",
        "score": score if score >= 0 else 100,  # unsupported → neutral, no penalty
        "weight": "medium",
        "findings": findings,
    }
