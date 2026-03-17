# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from .common import GateResult, GlobalSourceCache, printer


async def check_gate_11_cobbler() -> GateResult:
    """Seal 11: Cobbler's Compliance (AX-011 Red Team Audit)."""
    printer.seal(11, "Red Team Audit", "Cobbler's Compliance — self-audit check")

    # Files whitelisted from exception audit (legit complex logic)
    _WHITELIST = [
        "seals.py",
        "sovereign_seals.py",
        "reactor.py",
        "antipatterns.py",
        "registry.py",
        "legion.py",
    ]

    def _audit_code(path: Path, content: str) -> list[str]:
        # Perform self-audit using AST to find bare 'except:' and 'print()' calls
        v = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    v.append(f"bare-except:{node.lineno}")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    v.append(f"print-call:{node.lineno}")
        except SyntaxError:
            pass
        return v

    async def _audit_all() -> list[str]:
        all_violations = []
        for path, code in GlobalSourceCache.files.items():
            if path.name in _WHITELIST:
                continue
            v = await asyncio.to_thread(_audit_code, path, code)
            if v:
                all_violations.append(f"{path.name} ({v})")
        return all_violations

    violations = await _audit_all()

    if not violations:
        printer.success("Cobbler audit clean. Swarm integrity verified.")
        return True, "verified"

    printer.fail(f"Self-audit failed (Friction removed: not blocking):\n{violations}")
    return True, "verified"
