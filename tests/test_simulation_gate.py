"""Tests for SimulationGate + Anvil-Lang integration.

Validates:
  1. Structural TIS checks (empty ops, invalid chain)
  2. Anvil-lang formal verification via real CLI
  3. Full gate (TIS + Anvil) with C5-REAL promotion
  4. Edge cases (missing binary, missing file, timeout)

Requires: anvil-lang release binary built at
  ~/10_PROJECTS/anvil-lang/target/release/anvil
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cortex.verification.simulation import (
    AnvilVerification,
    SimulationGate,
    SimulationResult,
)
from cortex.extensions.security.tis_schema import TransactionIntentSchema

# Anvil binary and example paths
ANVIL_BINARY = Path.home() / "10_PROJECTS" / "anvil-lang" / "target" / "release" / "anvil"
ANV_HELLO = Path.home() / "10_PROJECTS" / "anvil-lang" / "examples" / "hello.anv"

# Skip condition for CI environments without anvil
requires_anvil = pytest.mark.skipif(
    not ANVIL_BINARY.exists(),
    reason="Anvil-lang binary not found (CI environment)",
)


def _make_tis(**overrides) -> TransactionIntentSchema:
    """Factory for test TIS instances."""
    defaults = {
        "intent_id": "test-001",
        "chain_id": 1,
        "sender": "0xDEAD",
        "operations": [{"type": "call", "target": "0xBEEF", "data": "0x"}],
        "metadata": {},
    }
    defaults.update(overrides)
    return TransactionIntentSchema(**defaults)


class TestSimulationResult:
    """Unit tests for structural TIS validation."""

    def test_empty_operations_denied(self) -> None:
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis(operations=[])
        result = asyncio.run(gate.simulate_tis(tis))
        assert not result.success
        assert result.revert_reason == "Empty operations list"
        assert result.reality_level == "C4-SIMULACIÓN"

    def test_invalid_chain_denied(self) -> None:
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis(chain_id=-1)
        result = asyncio.run(gate.simulate_tis(tis))
        assert not result.success
        assert "Invalid chain_id" in (result.revert_reason or "")

    def test_valid_tis_passes(self) -> None:
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis()
        result = asyncio.run(gate.simulate_tis(tis))
        assert result.success
        assert result.gas_used == 21_000
        assert result.reality_level == "C4-SIMULACIÓN"

    def test_multi_operation_gas(self) -> None:
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis(operations=[
            {"type": "call", "target": "0xA"},
            {"type": "transfer", "target": "0xB"},
            {"type": "deploy", "target": "0xC"},
        ])
        result = asyncio.run(gate.simulate_tis(tis))
        assert result.success
        assert result.gas_used == 63_000  # 21k × 3

    def test_state_diff_accuracy(self) -> None:
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis(operations=[
            {"type": "call", "target": "0xA"},
            {"type": "transfer", "target": "0xB"},
        ])
        result = asyncio.run(gate.simulate_tis(tis))
        assert result.state_diff["storage_slots_modified"] == 1  # call
        assert result.state_diff["events_emitted"] == 2  # call + transfer


class TestAnvilVerification:
    """Tests for Anvil-lang formal verification integration."""

    @requires_anvil
    def test_hello_anv_verifies(self) -> None:
        """hello.anv should fully verify (all_verified=True)."""
        gate = SimulationGate(use_anvil=True, anvil_binary=ANVIL_BINARY)
        result = asyncio.run(gate.verify_anv(ANV_HELLO))

        assert result.verified, f"Verification failed: {result.error}"
        assert result.functions_checked >= 1
        assert result.invariants_proven >= 1
        assert len(result.proof_hashes) >= 1
        assert result.reality_level == "C5-REAL"
        assert result.duration_ms > 0

    @requires_anvil
    def test_missing_file_returns_error(self) -> None:
        gate = SimulationGate(use_anvil=True, anvil_binary=ANVIL_BINARY)
        result = asyncio.run(gate.verify_anv(Path("/nonexistent/file.anv")))
        assert not result.verified
        assert "not found" in (result.error or "").lower()

    def test_anvil_disabled_returns_error(self) -> None:
        gate = SimulationGate(use_anvil=False)
        result = asyncio.run(gate.verify_anv(ANV_HELLO))
        assert not result.verified
        assert "not available" in (result.error or "").lower()

    def test_invalid_binary_path(self) -> None:
        gate = SimulationGate.__new__(SimulationGate)
        gate.use_anvil = True
        gate.anvil_binary = Path("/nonexistent/anvil")
        gate.timeout_seconds = 5
        result = asyncio.run(gate.verify_anv(ANV_HELLO))
        assert not result.verified


class TestFullGate:
    """Integration tests for the combined TIS + Anvil gate."""

    @requires_anvil
    def test_full_gate_c5_real_on_success(self) -> None:
        """When both TIS simulation and Anvil verify pass → C5-REAL."""
        gate = SimulationGate(use_anvil=True, anvil_binary=ANVIL_BINARY)
        tis = _make_tis()

        sim, anv = asyncio.run(gate.full_gate(tis, anv_path=ANV_HELLO))

        assert sim.success
        assert sim.reality_level == "C5-REAL"
        assert sim.proof_hash != ""
        assert anv is not None
        assert anv.verified

    def test_full_gate_no_anvil_stays_c4(self) -> None:
        """Without Anvil path, result stays C4-SIMULACIÓN."""
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis()

        sim, anv = asyncio.run(gate.full_gate(tis, anv_path=None))

        assert sim.success
        assert sim.reality_level == "C4-SIMULACIÓN"
        assert anv is None

    def test_full_gate_failed_tis_no_anvil_run(self) -> None:
        """If TIS fails structurally, Anvil still runs but reality stays C4."""
        gate = SimulationGate(use_anvil=False)
        tis = _make_tis(operations=[])

        sim, anv = asyncio.run(gate.full_gate(tis, anv_path=ANV_HELLO))

        assert not sim.success
        assert sim.reality_level == "C4-SIMULACIÓN"
