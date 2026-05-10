"""
CORTEX — Transaction Simulation Gate (Autodidact L2 → L2+).

Performs pre-execution validation via:
  1. Structural checks (empty ops, chain validation)
  2. Anvil-Lang formal verification (Z3 SMT proofs)
  3. PDR emission on every gate decision

Conformance: arXiv:2601.04583v1 §6.3 (Simulation Layer)
"""

import asyncio
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from cortex.guards.models import TransactionIntentSchema

logger = logging.getLogger("cortex.verification.simulation")

# Default Anvil-lang binary location
_DEFAULT_ANVIL_BINARY = Path.home() / "10_PROJECTS" / "anvil-lang" / "target" / "release" / "anvil"


@dataclass(frozen=True)
class SimulationResult:
    """Outcome of a transaction simulation."""
    success: bool
    state_diff: dict[str, Any] = field(default_factory=dict)
    revert_reason: Optional[str] = None
    gas_used: int = 0
    reality_level: str = "C4-SIMULACIÓN"
    proof_hash: str = ""
    anvil_output: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class AnvilVerification:
    """Result of an Anvil-lang formal verification run."""
    verified: bool
    functions_checked: int = 0
    invariants_proven: int = 0
    proof_hashes: list[str] = field(default_factory=list)
    counterexamples: list[dict[str, Any]] = field(default_factory=list)
    raw_output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0

    @property
    def reality_level(self) -> str:
        """C5-REAL if all proofs pass, C4-SIMULACIÓN otherwise."""
        return "C5-REAL" if self.verified and self.functions_checked > 0 else "C4-SIMULACIÓN"


class SimulationGate:
    """Validator for Transaction Intents using state-fork simulation + Anvil-lang proofs.

    L2 conformance: Structural checks + Anvil formal verification.
    All decisions emit PDR-compatible evidence.
    """

    def __init__(
        self,
        use_anvil: bool = True,
        anvil_binary: Optional[Path] = None,
        timeout_seconds: int = 30,
    ):
        self.use_anvil = use_anvil
        self.anvil_binary = anvil_binary or _DEFAULT_ANVIL_BINARY
        self.timeout_seconds = timeout_seconds

        # Validate binary exists at init time
        if self.use_anvil and not self.anvil_binary.exists():
            resolved = shutil.which("anvil")
            if resolved and "anvil-lang" in resolved:
                self.anvil_binary = Path(resolved)
            else:
                logger.warning(
                    "Anvil binary not found at %s. Falling back to C4-SIMULACIÓN mode.",
                    self.anvil_binary,
                )
                self.use_anvil = False

    # ─── Core Simulation ───────────────────────────────────────

    async def simulate_tis(self, tis: TransactionIntentSchema) -> SimulationResult:
        """Simulate a TIS and return the expected state diff.

        Args:
            tis: The Transaction Intent to simulate.

        Returns:
            SimulationResult with success status, state diff, and proof metadata.
        """
        logger.info("Simulating intent %s on chain %s...", tis.intent_id, tis.chain_id)

        # Gate 1: Structural validation
        if not tis.operations:
            return SimulationResult(
                success=False,
                revert_reason="Empty operations list",
                reality_level="C4-SIMULACIÓN",
            )

        # Gate 2: Chain validation
        if tis.chain_id <= 0:
            return SimulationResult(
                success=False,
                revert_reason=f"Invalid chain_id: {tis.chain_id}",
                reality_level="C4-SIMULACIÓN",
            )

        # Gate 3: Compute state diff from operations
        state_diff = self._compute_state_diff(tis)

        return SimulationResult(
            success=True,
            state_diff=state_diff,
            gas_used=21_000 * len(tis.operations),
            reality_level="C4-SIMULACIÓN",
        )

    # ─── Anvil-Lang Formal Verification ────────────────────────

    async def verify_anv(self, anv_path: Path) -> AnvilVerification:
        """Run Anvil-lang formal verification on a .anv file.

        Invokes the Anvil CLI with --json output and parses the structured result.
        This is the L2+ gate: if all invariants are proven, the result is C5-REAL.

        Args:
            anv_path: Path to the .anv source file.

        Returns:
            AnvilVerification with proof hashes and counterexamples.
        """
        if not self.use_anvil:
            return AnvilVerification(
                verified=False,
                error="Anvil-lang not available (C4-SIMULACIÓN fallback)",
            )

        if not anv_path.exists():
            return AnvilVerification(
                verified=False,
                error=f"File not found: {anv_path}",
            )

        logger.info("Anvil-lang: verifying %s ...", anv_path.name)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [str(self.anvil_binary), "check", "--json", str(anv_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return AnvilVerification(
                verified=False,
                error=f"Verification timed out after {self.timeout_seconds}s",
            )
        except FileNotFoundError:
            return AnvilVerification(
                verified=False,
                error=f"Anvil binary not found at {self.anvil_binary}",
            )

        # Parse JSON from stdout (anvil outputs structured JSON on last line)
        raw_json = self._extract_json(result.stdout)
        if raw_json is None:
            return AnvilVerification(
                verified=False,
                error=f"Failed to parse Anvil output: {result.stderr[:500]}",
            )

        # Extract structured fields
        all_verified = raw_json.get("all_verified", False)
        results = raw_json.get("results", [])

        proof_hashes = [
            r["proof_hash"] for r in results
            if r.get("verified") and r.get("proof_hash")
        ]

        counterexamples = [
            {"fn_name": r["fn_name"], "counterexample": r["counterexample"]}
            for r in results
            if not r.get("verified") and r.get("counterexample")
        ]

        total_invariants = sum(r.get("invariants", 0) for r in results)
        total_duration = sum(r.get("duration_ms", 0) for r in results)

        verification = AnvilVerification(
            verified=all_verified,
            functions_checked=raw_json.get("functions", 0),
            invariants_proven=total_invariants if all_verified else 0,
            proof_hashes=proof_hashes,
            counterexamples=counterexamples,
            raw_output=raw_json,
            duration_ms=total_duration,
        )

        if all_verified:
            logger.info(
                "Anvil-lang: ✅ VERIFIED (%d functions, %d invariants, %.1fms)",
                verification.functions_checked,
                verification.invariants_proven,
                total_duration,
            )
        else:
            logger.warning(
                "Anvil-lang: ❌ FAILED (%d counterexamples found)",
                len(counterexamples),
            )

        return verification

    # ─── Combined Gate (TIS + Anvil) ───────────────────────────

    async def full_gate(
        self,
        tis: TransactionIntentSchema,
        anv_path: Optional[Path] = None,
    ) -> tuple[SimulationResult, Optional[AnvilVerification]]:
        """Run both simulation and formal verification.

        Returns:
            Tuple of (SimulationResult, AnvilVerification or None).
        """
        sim_result = await self.simulate_tis(tis)

        anv_result = None
        if anv_path and self.use_anvil:
            anv_result = await self.verify_anv(anv_path)

            # Upgrade reality level if both pass
            if sim_result.success and anv_result.verified:
                # Create new SimulationResult with C5-REAL
                sim_result = SimulationResult(
                    success=True,
                    state_diff=sim_result.state_diff,
                    gas_used=sim_result.gas_used,
                    reality_level="C5-REAL",
                    proof_hash=anv_result.proof_hashes[0] if anv_result.proof_hashes else "",
                    anvil_output=anv_result.raw_output,
                )

        return sim_result, anv_result

    # ─── Private Helpers ───────────────────────────────────────

    @staticmethod
    def _compute_state_diff(tis: TransactionIntentSchema) -> dict[str, Any]:
        """Compute a synthetic state diff from TIS operations."""
        diff: dict[str, Any] = {
            "operations_count": len(tis.operations),
            "chain_id": tis.chain_id,
            "storage_slots_modified": 0,
            "events_emitted": 0,
        }

        for op in tis.operations:
            op_type = op.get("type", "unknown")
            if op_type == "transfer":
                diff["events_emitted"] += 1
            elif op_type == "call":
                diff["storage_slots_modified"] += 1
                diff["events_emitted"] += 1
            elif op_type == "deploy":
                diff["storage_slots_modified"] += op.get("storage_size", 1)

        return diff

    @staticmethod
    def _extract_json(output: str) -> Optional[dict[str, Any]]:
        """Extract the JSON object from Anvil CLI output.

        Anvil may emit log lines before the JSON. We scan for the
        last line that starts with '{'.
        """
        for line in reversed(output.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None
