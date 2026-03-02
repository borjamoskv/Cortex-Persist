"""
LEGION-OMEGA: Red Team Attack Vectors.
Specialized agents designed to destroy, hack, or saturate proposed code.
"""

from __future__ import annotations

import ast
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AttackVector(Protocol):
    """Sovereign Attack Vector Interface."""

    name: str

    async def attack(self, code: str, context: dict[str, Any]) -> list[str]:
        """Sows entropy and returns detected vulnerabilities."""
        ...


class OOMKiller:
    """Vector: Memory Exhaustion (The OOM Killer)."""

    name = "oom_killer"

    async def attack(self, code: str, context: dict[str, Any]) -> list[str]:
        findings = []
        try:
            tree = ast.parse(code)
            # Search for infinite loops or massive allocations
            for node in ast.walk(tree):
                if isinstance(node, (ast.While, ast.For)):
                    # Simulating a heuristic check for unprotected loops
                    if not any(isinstance(n, ast.Break) for n in ast.walk(node)):
                        # This is a simplified check for demo purposes
                        pass

            # Simulated stress: Check for large list comprehensions without bounds
            if "range(" in code and "10**" in code:
                findings.append("Potential memory exhaustion: unbound range/allocation detected.")
        except Exception:
            pass
        return findings


class Intruder:
    """Vector: Injection & Security Bypass (The Intruder)."""

    name = "intruder"

    async def attack(self, code: str, context: dict[str, Any]) -> list[str]:
        findings = []
        # Check for raw eval/exec (ignore literal_eval)
        for pattern in ["eval(", "exec("]:
            if pattern in code and f"ast.literal_{pattern}" not in code:
                findings.append(f"Security Vulnerability: Use of dangerous function `{pattern}`.")

        # Check for system calls
        for pattern in ["os.system(", "subprocess.run(shell=True)"]:
            if pattern in code:
                findings.append(f"Security Vulnerability: Use of dangerous function `{pattern}`.")

        # AST analysis for more subtle injections
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "__globals__":
                    findings.append("Dunder access detected: Potential sandbox escape.")
        except Exception:
            pass
        return findings


class EntropyDemon:
    """Vector: Chaos & Edge Case Annihilation (The Entropy Demon)."""

    name = "entropy_demon"

    async def attack(self, code: str, context: dict[str, Any]) -> list[str]:
        findings = []
        # Checks for missing null-safety and generic exception handling
        if "except Exception:" in code or "except:" in code:
            findings.append(
                "Fragility: Bare `except` detected. System cannot tolerate undetected entropy."
            )

        if ".get(" not in code and "[" in code and "]" in code:
            findings.append("Unsafe access: Potential KeyError/IndexError under entropy.")

        return findings


class ChronosSniper:
    """Vector: Asynchrony Race Conditions (The Chronos Sniper)."""

    name = "chronos_sniper"

    async def attack(self, code: str, context: dict[str, Any]) -> list[str]:
        findings = []
        # Checks for blocking calls in async def
        blocking = ["time.sleep(", "requests.get("]
        if "async def" in code:
            for b in blocking:
                if b in code:
                    findings.append(f"Async Violation: Blocking call `{b}` inside async function.")
        elif "sleep" in context.get("intent", "").lower() and "import asyncio" not in code:
            # If intent wants sleep/async but code is sync blocking
            findings.append(
                "Blocking Logic: Synchronous `time.sleep` in logic that requires asynchrony."
            )

            # Check for shared state without locks in pseudo-code intent
            if "global " in code:
                findings.append(
                    "Race Condition: Use of `global` in async context without explicit locking."
                )

        return findings


RED_TEAM_SWARM = [OOMKiller(), Intruder(), EntropyDemon(), ChronosSniper()]
