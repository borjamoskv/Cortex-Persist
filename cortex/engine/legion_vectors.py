"""
LEGION-OMEGA: Red Team Attack Vectors.
Specialized agents designed to destroy, breach, or saturate proposed code.
"""

from __future__ import annotations

import ast
import logging
import re
from collections.abc import Mapping
from typing import Any, Protocol

from cortex.utils.respiration import oxygenate

logger = logging.getLogger(__name__)

__all__ = [
    "AttackVector",
    "OOMKiller",
    "Intruder",
    "EntropyDemon",
    "ChronosSniper",
    "RED_TEAM_SWARM",
]


class AttackVector(Protocol):
    """Sovereign Attack Vector Interface."""

    name: str


class OOMKiller:
    """Vector: Memory Exhaustion (The OOM Killer)."""

    name = "oom_killer"

    @oxygenate(min_interval=0.01)
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        try:
            tree = ast.parse(code)
            # Search for infinite loops or massive allocations
            for node in ast.walk(tree):
                if isinstance(node, ast.While | ast.For):
                    if not any(isinstance(n, ast.Break) for n in ast.walk(node)):
                        findings.append(
                            "Potential infinite loop: loop without break statement detected."
                        )

            # Simulated stress: Check for large list comprehensions without bounds
            if "range(" in code and "10**" in code:
                findings.append("Potential memory exhaustion: unbound range/allocation detected.")
        except SyntaxError:
            logger.debug("OOMKiller: Failed to parse code for analysis.")
        return findings


class Intruder:
    """Vector: Injection & Security Bypass (The Intruder)."""

    name = "intruder"

    def _check_dangerous_funcs(self, code: str) -> list[str]:
        findings = []
        _safe_exec = ("ast.literal_eval(", "create_subprocess_exec(", "subprocess_exec")
        for pattern in ["eval(", "exec("]:
            if pattern in code:
                occurrences = [m.start() for m in re.finditer(re.escape(pattern), code)]
                for pos in occurrences:
                    ctx = code[max(0, pos - 25) : pos + len(pattern)]
                    if not any(safe in ctx for safe in _safe_exec):
                        findings.append(
                            f"Security Vulnerability: Use of dangerous function `{pattern}`."
                        )
                        break

        for pattern in ["os.system(", "subprocess.run(shell=True)"]:
            if pattern in code:
                findings.append(f"Security Vulnerability: Use of dangerous function `{pattern}`.")
        return findings

    def _check_ast(self, code: str) -> list[str]:
        findings = []
        try:
            for node in ast.walk(ast.parse(code)):
                if isinstance(node, ast.Attribute) and node.attr == "__globals__":
                    findings.append("Dunder access detected: Potential sandbox escape.")
        except SyntaxError:
            logger.debug("Intruder: Failed to parse code for AST analysis.")
        return findings

    @oxygenate(min_interval=0.01)
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = self._check_dangerous_funcs(code)
        findings.extend(self._check_ast(code))
        return findings


class EntropyDemon:
    """Vector: Chaos & Edge Case Annihilation (The Entropy Demon)."""

    name = "entropy_demon"

    @oxygenate(min_interval=0.01)
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        # Checks for missing null-safety and generic exception handling
        if "except Exception:  # noqa: BLE001" in code or "except:" in code:
            findings.append(
                "Fragility: Bare `except` detected. System cannot tolerate undetected entropy."
            )

        if ".get(" not in code and "[" in code and "]" in code:
            findings.append("Unsafe access: Potential KeyError/IndexError under entropy.")

        return findings


class ChronosSniper:
    """Vector: Asynchrony Race Conditions (The Chronos Sniper)."""

    name = "chronos_sniper"

    @oxygenate(min_interval=0.01)
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
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


class SiegeVector(Protocol):
    """Runtime Siege Vector Interface for live system attacks."""

    name: str


class LedgerPoisoner:
    """Vector: Cryptographic Hash Poisoning (The Ledger Poisoner)."""

    name = "ledger_poisoner"

    async def attack(self, system: Any, context: Mapping[str, Any]) -> list[str]:
        findings = []
        try:
            # We assume system is an instance of AsyncCortexEngine
            pool = system.pool
            async with pool.acquire() as conn:
                # Attempt to corrupt a random transaction
                cursor = await conn.execute("SELECT id FROM transactions ORDER BY RANDOM() LIMIT 1")
                row = await cursor.fetchone()
                if row:
                    tx_id = row[0]
                    try:
                        await conn.execute(
                            "UPDATE transactions SET hash = 'POISONED_HASH_12345' WHERE id = ?",
                            (tx_id,),
                        )
                        await conn.commit()
                        findings.append(
                            f"LedgerPoisoner: Corrupted transaction #{tx_id} via UPDATE."
                        )
                    except Exception as e:  # noqa: BLE001 — expected DB rejection for attack
                        logger.debug("LedgerPoisoner Update rejected by DB (expected): %s", e)

                # Attempt to delete a Merkle root
                try:
                    await conn.execute("DELETE FROM merkle_roots WHERE id > 0")
                    await conn.commit()
                    findings.append(
                        "LedgerPoisoner: Dropped Merkle checkpoints via raw SQL DELETE."
                    )
                except Exception as e:  # noqa: BLE001 — expected DB rejection for attack
                    logger.debug("LedgerPoisoner Delete rejected by DB (expected): %s", e)

        except Exception as e:  # noqa: BLE001 — attack vector execution boundary
            logger.debug("LedgerPoisoner execution error: %s", e)

        return findings


class VaultCracker:
    """Vector: AES-GCM Entropy Cracker (The Vault Cracker)."""

    name = "vault_cracker"

    async def attack(self, system: Any, context: Mapping[str, Any]) -> list[str]:
        findings = []
        try:
            vault = getattr(system, "vault", None)
            if not vault or not getattr(vault, "is_available", False):
                return ["VaultCracker: Vault is disabled or missing key."]

            # Test 1: Malleability detection
            content = "FACT_ENCRYPTED_CONTENT_STUB"
            tampered = content[:-5] + "XXXXX"
            try:
                vault.decrypt(tampered)
                findings.append(
                    "VaultCracker: Malleability attack succeeded (authentication failed)."
                )
            except Exception:  # noqa: BLE001 — expected decryption failure
                pass  # Success = Tag caught it

        except Exception as e:  # noqa: BLE001 — attack vector execution boundary
            logger.debug("VaultCracker error: %s", e)

        return findings


class EpistemicJustice:
    """Vector: Epistemic Injustice Audit (Miranda Fricker Protocol).

    Detects patterns where subjects are discredited or misunderstood due to
    identity prejudice (Testimonial) or lack of conceptual resources (Hermeneutical).
    """

    name = "epistemic_justice"

    async def attack(self, system: Any, context: dict[str, Any]) -> list[str]:
        findings = []
        source_code = getattr(system, "source_code", "")
        prejudice_proxies = [
            r"zip_code",
            r"neighborhood",
            r"postal_code",
            r"surname_origin",
            r"ethnicity",
            r"gender_proxy",
            r"education_level_bias",
        ]

        for proxy in prejudice_proxies:
            if re.search(rf"\b{proxy}\b", source_code, re.IGNORECASE):
                findings.append(
                    f"Testimonial Injustice: Logic uses '{proxy}' as a credibility filter. "
                    "This discredits the subject for reasons unrelated to content "
                    "(Identity Prejudice)."
                )

        if "switch" in source_code or "if" in source_code:
            if "default" not in source_code.lower() and "else" not in source_code.lower():
                findings.append(
                    "Hermeneutical Injustice: Rigid classification detected without open-ended "
                    "interpretative resources. Systemic disadvantage for non-standard "
                    "social experiences."
                )

        return findings


RED_TEAM_SWARM = {v.name: v for v in (OOMKiller(), Intruder(), EntropyDemon(), ChronosSniper())}
COMPLIANCE_SIEGE_SWARM = {v.name: v for v in (LedgerPoisoner(), VaultCracker(), EpistemicJustice())}
