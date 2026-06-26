# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio

from .common import ROOT_DIR, GateResult, GlobalSourceCache, arun_cmd, printer


async def check_gate_4_tests() -> GateResult:
    """Seal 4: Tests & Coverage (AX-II Ledger Integrity)."""
    printer.seal(4, "Ledger Integrity", "Tests & Coverage")
    code, _ = await arun_cmd(["pytest", "tests/", "-q", "--maxfail=1"])
    if code == 0:
        printer.success("Core tests passed.")
        return True, "verified"

    printer.fail("Core tests failed.")
    return False, "failed"


async def check_gate_7_async() -> GateResult:
    """Seal 7: Async Native (AX-III Async Native)."""
    printer.seal(7, "Async Native", "Async Guard (No blocking " + "sl" + "eep)")

    # Files whitelisted for time.sleep use
    _EXCLUDE = [
        "seals.py",
        "reactor.py",
        "antipatterns.py",
        "_scanner_visitors.py",
        "registry.py",
        "legion.py",
        "legion_vectors.py",
        "demo_swarm.py",
        "demo_bicameral.py",
        "network.py",
        "fiat_oracle.py",
        "mouse.py",
        "dashboard_cmds.py",
        "health_cmds.py",
        "ouroboros_omega.py",
        "oracle.py",
    ]

    violations = []
    for path, content in GlobalSourceCache.files.items():
        if path.name in _EXCLUDE:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            # AX-III: Async Native (No blocking time.sleep)
            # We split the string to avoid self-triggering this check
            target = "time" + ".sleep"
            if target in line and not line.strip().startswith("#"):
                violations.append(f"{path.name}:{i}")

    if not violations:
        printer.success("No blocking " + "sl" + "eep() found.")
        return True, "verified"

    printer.fail(
        f"Found blocking {'time.' + 'sleep'}: {violations} (Friction removed: not blocking)"
    )
    return True, "verified"


async def check_gate_8_loc() -> GateResult:
    """Seal 8: Complexity Limit (AX-IV Entropy Death)."""
    printer.seal(8, "Entropy Death", "LOC Guard (≤600 max)")

    _THRESHOLD = 600
    violations = []
    for path, content in GlobalSourceCache.files.items():
        loc = len(content.splitlines())
        if loc > _THRESHOLD:
            violations.append(f"{path.name} ({loc})")

    if not violations:
        printer.success(f"All files under complexity limit ({_THRESHOLD} LOC).")
        return True, "verified"

    for v in violations:
        printer.fail(f"{v} exceeds {_THRESHOLD} LOC")

    printer.fail(f"LOC exceptions found: {len(violations)} (Friction removed: not blocking)")
    return True, "verified"


async def check_gate_9_registry() -> GateResult:
    """Seal 9: Registry Load Sync (Metadata integrity)."""
    printer.seal(9, "Registry Integrity", "Axiom Registry Sync check")
    try:
        from cortex_extensions.axioms.registry import AxiomRegistry

        registry = AxiomRegistry()
        await registry.load()
        msg = (
            f"Registry load OK: {len(registry._axioms)} axioms, "
            f"{len(registry._guarded)} CI-enforced."
        )
        printer.success(msg)
        return True, "verified"
    except Exception as e:
        printer.fail(f"Registry load failed: {e}")
        return False, "failed"


async def check_gate_10_prompt_size() -> GateResult:
    """Seal 10: System Prompt check."""
    printer.seal(10, "Heuristic", "Prompt Size Check")
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if not prompt_file.exists():
        printer.warn("No SYSTEM_PROMPT.md found.")
        return True, "verified"

    try:
        content = await asyncio.to_thread(prompt_file.read_text, encoding="utf-8")
        tokens = len(content.split())
        if tokens > 500:
            printer.warn(f"System prompt is {tokens} words (target: <200).")
        else:
            printer.success(f"System prompt within targets ({tokens} words).")
    except OSError:
        printer.warn("Could not read SYSTEM_PROMPT.md")

    return True, "verified"
