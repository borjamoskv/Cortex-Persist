#!/usr/bin/env python3
"""CORTEX Vanguard Daemon — Autonomous Bounty Extraction Engine.

V9: All execution phases gated by SecurityMonitorClassifier
and stochastic commands routed through StochasticSandbox.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from typing import List

# Configuración Termodinámica
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR = os.path.join(BASE_DIR, "targets")
LEDGER_PATH = os.path.join(BASE_DIR, "vanguard_ledger.json")
HEARTBEAT_SEC = 3600


def log(msg: str, tier: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{tier}] [VANGUARD-DAEMON] {msg}")


def update_ledger(
    target: str,
    status: str,
    details: str = "",
) -> None:
    ledger = {}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger = json.load(f)
        except Exception:
            ledger = {}

    ledger[target] = {
        "last_seen": datetime.now().isoformat(),
        "status": status,
        "details": details,
    }

    ledger_dir = os.path.dirname(LEDGER_PATH) or "."
    with tempfile.NamedTemporaryFile(
        "w",
        dir=ledger_dir,
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        json.dump(ledger, tmp_file, indent=2)
        tmp_path = tmp_file.name
    os.replace(tmp_path, LEDGER_PATH)


def _classify_cmd(cmd_str: str, phase: str) -> bool:
    """Gate a command through SecurityMonitorClassifier.

    Returns True if the command is allowed, False if blocked.
    """
    try:
        from cortex.extensions.security.security_monitor import (
            ParameterProvenance,
            SecurityMonitorClassifier,
        )

        monitor = SecurityMonitorClassifier()
        task = {
            "command": cmd_str,
            "agent": f"vanguard-{phase}",
        }
        verdict = monitor.classify(
            task,
            user_request="Vanguard bounty extraction cycle",
            provenance=ParameterProvenance.AGENT_INFERRED,
        )
        if not verdict.allowed:
            log(
                f"BLOCKED by SecurityMonitor [{phase}]: "
                f"{verdict.reason}",
                "SECURITY",
            )
            return False
        return True
    except ImportError:
        # SecurityMonitor not available — allow with warning
        log("SecurityMonitor unavailable, proceeding", "WARN")
        return True


def _sandbox_cmd(
    cmd_str: str, cwd: str
) -> tuple[str, str]:
    """Route stochastic commands through StochasticSandbox.

    Returns (possibly_rewritten_cmd, arena_path_or_empty).
    """
    try:
        from cortex.extensions.security.stochastic_sandbox import (
            StochasticSandbox,
        )

        sandbox = StochasticSandbox()
        result = sandbox.intercept(cmd_str, cwd=cwd)
        if result.is_redirected:
            log(
                f"SANDBOXED [{result.matched_pattern}]:"
                f" {cwd} → {result.arena_path}",
                "SANDBOX",
            )
            return result.redirected_cmd, result.arena_path
        return cmd_str, ""
    except ImportError:
        return cmd_str, ""


async def run_step(
    name: str,
    cmd: List[str],
    cwd: str = BASE_DIR,
) -> str:
    """Execute a phase with V9 security gating."""
    cmd_str = " ".join(cmd)

    # Phase 1: Intent classification
    if not _classify_cmd(cmd_str, name):
        return f"[BLOCKED] Phase {name} denied by SecurityMonitor"

    # Phase 2: Stochastic sandbox redirect
    final_cmd, arena = _sandbox_cmd(cmd_str, cwd)
    effective_cwd = arena if arena else cwd

    log(f"Iniciando fase: {name}", "EXEC")

    # Robust Subprocess Execution (Ω-Hardened)
    vanguard_env = os.environ.copy()
    vanguard_env["PYTHONUNBUFFERED"] = "1"
    base_pythonpath = os.path.dirname(BASE_DIR.rstrip("/"))
    existing_pythonpath = vanguard_env.get("PYTHONPATH")
    vanguard_env["PYTHONPATH"] = (
        f"{base_pythonpath}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else base_pythonpath
    )

    if arena:
        process = await asyncio.create_subprocess_exec(
            "/bin/sh",
            "-lc",
            final_cmd,
            cwd=effective_cwd,
            env=vanguard_env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=effective_cwd,
            env=vanguard_env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    stdout, stderr = await process.communicate()
    output = (
        stdout.decode().strip()
        + stderr.decode().strip()
    )

    if process.returncode == 0:
        log(f"Fase {name} completada.", "SUCCESS")
    else:
        log(
            f"Fase {name} anomalías "
            f"(Exit: {process.returncode}).",
            "WARN",
        )

    # Phase 3: Arena cleanup
    if arena:
        try:
            from cortex.extensions.security.stochastic_sandbox import (
                StochasticSandbox,
            )
            StochasticSandbox().cleanup(arena)
        except Exception as e:
            log(f"Arena cleanup failed: {e}", "WARN")

    return output


async def vanguard_cycle():
    log(
        "=== CICLO VANGUARD-OMEGA (V9 Hardened) ===",
        "SINGULARITY",
    )

    # 1. SCOUT: Ingesta de Immunefi
    log("Scout L4: actualizando targets...", "STEP")
    await run_step(
        "IMMUNEFI-SCOUT",
        ["python3", "cortex_immunefi_scout.py"],
    )

    # Leer targets reales
    targets_json = os.path.join(
        BASE_DIR, "real_bounties.json"
    )
    if not os.path.exists(targets_json):
        log("No se encontró real_bounties.json", "ERROR")
        return

    with open(targets_json, "r") as f:
        targets_data = json.load(f)

    for target_info in targets_data:
        name = (
            target_info.get("protocol")
            or target_info.get("target")
            or "Unknown"
        ).replace(" ", "_").lower()
        target_path = os.path.join(TARGETS_DIR, name)

        if not os.path.exists(target_path):
            log(f"Target {name} no clonado.", "SKIP")
            continue

        log(f"Asaltando: {name.upper()}...", "ATTACK")

        # 2. FRACTOR: Análisis AST (R0 — read-only)
        out_ast = await run_step(
            f"AST-{name}",
            [
                "python3",
                "cortex_ast_fractor.py",
                target_path,
            ],
        )

        # 3. CHAOS: Fuzzing (STOCHASTIC — sandboxed)
        out_chaos = await run_step(
            f"CHAOS-{name}",
            [
                "python3",
                "cortex_chaos_fuzzer.py",
                target_path,
                "50000",
            ],
        )

        # 4. LEDGER: Registro de resultados
        status = (
            "FRACTURED"
            if "BREAKER" in out_chaos
            else "RESISTANT"
        )
        update_ledger(name, status, out_chaos[-500:])

        if status == "FRACTURED":
            log(
                f"!!! COLISIÓN EN {name.upper()} !!!",
                "CRITICAL",
            )

    log(
        f"Ciclo completado. Hibernando {HEARTBEAT_SEC}s",
        "IDLE",
    )


async def main():
    if "--once" in sys.argv:
        await vanguard_cycle()
        return

    while True:
        try:
            await vanguard_cycle()
        except Exception as e:
            log(f"Falla motor central: {e}", "FATAL")

        await asyncio.sleep(HEARTBEAT_SEC)


if __name__ == "__main__":
    asyncio.run(main())
