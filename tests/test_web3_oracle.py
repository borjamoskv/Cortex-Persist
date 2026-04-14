"""Tests for cortex.extensions.web3.oracle — OuroborosOracle.

Validates epistemic-health evaluation, pulse decision logic, and ledger
persistence without requiring a live RPC or a real CortexEngine.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

import pytest

from cortex.extensions.immune.breaker import EpistemicState
from cortex.extensions.web3.oracle import (
    _ENTROPY_THRESHOLD,
    _LOCKED_STATE,
    OuroborosOracle,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    test_failures: int = 0,
    ghosts: int = 0,
    linting: int = 0,
) -> EpistemicState:
    return EpistemicState(
        consecutive_test_failures=test_failures,
        unresolved_ghosts=ghosts,
        recent_linting_mutations=linting,
    )


def _make_engine(system_state: str = "ACTIVE") -> MagicMock:
    engine = MagicMock()
    engine.system_state = system_state
    engine.store = AsyncMock(return_value=1)
    return engine


# ---------------------------------------------------------------------------
# Entropy threshold constant
# ---------------------------------------------------------------------------


def test_entropy_threshold_value() -> None:
    assert _ENTROPY_THRESHOLD == 50.0


def test_locked_state_sentinel() -> None:
    assert _LOCKED_STATE == "LOCKED_EPISTEMIC_HALT"


# ---------------------------------------------------------------------------
# Constructor / env var resolution
# ---------------------------------------------------------------------------


class TestOuroborosOracleInit:
    def test_explicit_params(self) -> None:
        oracle = OuroborosOracle(
            rpc_url="http://localhost:8545",
            private_key="0xdeadbeef",
            contract_address="0x1234",
        )
        assert oracle._rpc_url == "http://localhost:8545"
        assert oracle._private_key == "0xdeadbeef"
        assert oracle._contract_address == "0x1234"

    def test_falls_back_to_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEB3_RPC_URL", "http://rpc.example.com")
        monkeypatch.setenv("WEB3_PRIVATE_KEY", "0xabcdef")
        monkeypatch.setenv("OUROBOROS_CONTRACT_ADDRESS", "0x5678")

        oracle = OuroborosOracle()
        assert oracle._rpc_url == "http://rpc.example.com"
        assert oracle._private_key == "0xabcdef"
        assert oracle._contract_address == "0x5678"

    def test_defaults_when_env_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("WEB3_RPC_URL", raising=False)
        monkeypatch.delenv("WEB3_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("OUROBOROS_CONTRACT_ADDRESS", raising=False)

        oracle = OuroborosOracle()
        assert oracle._rpc_url == ""
        assert oracle._private_key is None
        assert oracle._contract_address is None


# ---------------------------------------------------------------------------
# Pulse withheld: high entropy
# ---------------------------------------------------------------------------


class TestPulseWithheldHighEntropy:
    @pytest.mark.asyncio
    async def test_withheld_when_entropy_at_threshold(self) -> None:
        oracle = OuroborosOracle()
        # ED = 1*15 + 2*10 + 1*5 = 40 — below threshold, but let's use 4 failures
        # 4*15 = 60 > 50
        state = _make_state(test_failures=4)
        assert state.entropy_density >= _ENTROPY_THRESHOLD

        result = await oracle.run_pulse_cycle(state)
        assert result["action"] == "PULSE_WITHHELD"
        assert result["entropy_density"] == state.entropy_density

    @pytest.mark.asyncio
    async def test_withheld_persists_to_ledger(self) -> None:
        engine = _make_engine()
        oracle = OuroborosOracle()
        state = _make_state(test_failures=4)

        await oracle.run_pulse_cycle(state, engine=engine)

        engine.store.assert_awaited_once()
        call_kwargs: dict[str, Any] = engine.store.call_args.kwargs
        assert call_kwargs.get("fact_type") == "decision"
        assert "pulse_withheld" in call_kwargs.get("tags", [])
        meta = call_kwargs.get("meta", {})
        assert "payload_sha256" in meta
        assert len(meta["payload_sha256"]) == 64  # SHA-256 hex digest

    @pytest.mark.asyncio
    async def test_withheld_reason_mentions_entropy(self) -> None:
        oracle = OuroborosOracle()
        state = _make_state(test_failures=4)
        result = await oracle.run_pulse_cycle(state)
        assert "entropy" in result["reason"].lower() or "Entropy" in result["reason"]


# ---------------------------------------------------------------------------
# Pulse withheld: LOCKED_EPISTEMIC_HALT
# ---------------------------------------------------------------------------


class TestPulseWithheldLockedState:
    @pytest.mark.asyncio
    async def test_withheld_when_system_locked(self) -> None:
        engine = _make_engine(system_state=_LOCKED_STATE)
        oracle = OuroborosOracle()
        # Low entropy — healthy system, but locked
        state = _make_state(test_failures=0)
        assert state.entropy_density < _ENTROPY_THRESHOLD

        result = await oracle.run_pulse_cycle(state, engine=engine)
        assert result["action"] == "PULSE_WITHHELD"
        assert result["locked"] is True

    @pytest.mark.asyncio
    async def test_withheld_reason_mentions_halt(self) -> None:
        engine = _make_engine(system_state=_LOCKED_STATE)
        oracle = OuroborosOracle()
        state = _make_state()
        result = await oracle.run_pulse_cycle(state, engine=engine)
        assert _LOCKED_STATE in result["reason"]


# ---------------------------------------------------------------------------
# Pulse attempted: healthy system with missing Web3 config
# ---------------------------------------------------------------------------


class TestPulseSimulationMode:
    @pytest.mark.asyncio
    async def test_withheld_without_rpc_config(self) -> None:
        oracle = OuroborosOracle(rpc_url="", private_key=None, contract_address=None)
        state = _make_state(test_failures=0)
        assert state.entropy_density < _ENTROPY_THRESHOLD

        result = await oracle.run_pulse_cycle(state)
        assert result["action"] == "PULSE_WITHHELD"
        assert "simulation" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_simulation_mode_still_persists_to_ledger(self) -> None:
        engine = _make_engine()
        oracle = OuroborosOracle(rpc_url="", private_key=None, contract_address=None)
        state = _make_state()

        await oracle.run_pulse_cycle(state, engine=engine)
        engine.store.assert_awaited_once()


# ---------------------------------------------------------------------------
# Pulse sent: healthy system with Web3 config mocked
# ---------------------------------------------------------------------------


class TestPulseSentHealthySystem:
    @pytest.mark.asyncio
    async def test_pulse_sent_on_healthy_state(self) -> None:
        oracle = OuroborosOracle(
            rpc_url="http://localhost:8545",
            private_key="0xdeadbeef",
            contract_address="0xCAFE",
        )
        state = _make_state(test_failures=0, ghosts=0, linting=0)
        assert state.entropy_density < _ENTROPY_THRESHOLD

        with patch.object(
            oracle,
            "_send_pulse_transaction",
            return_value={"success": True, "tx_hash": "0xabc123", "block_number": 999},
        ):
            result = await oracle.run_pulse_cycle(state)

        assert result["action"] == "PULSE_SENT"
        assert result["tx_hash"] == "0xabc123"
        assert result["block_number"] == 999

    @pytest.mark.asyncio
    async def test_pulse_sent_is_persisted_to_ledger(self) -> None:
        engine = _make_engine()
        oracle = OuroborosOracle(
            rpc_url="http://localhost:8545",
            private_key="0xdeadbeef",
            contract_address="0xCAFE",
        )
        state = _make_state()

        with patch.object(
            oracle,
            "_send_pulse_transaction",
            return_value={"success": True, "tx_hash": "0xabc123", "block_number": 1},
        ):
            await oracle.run_pulse_cycle(state, engine=engine)

        engine.store.assert_awaited_once()
        call_kwargs = engine.store.call_args.kwargs
        assert "pulse_sent" in call_kwargs.get("tags", [])

    @pytest.mark.asyncio
    async def test_reverted_tx_produces_withheld_action(self) -> None:
        engine = _make_engine()
        oracle = OuroborosOracle(
            rpc_url="http://localhost:8545",
            private_key="0xdeadbeef",
            contract_address="0xCAFE",
        )
        state = _make_state()

        with patch.object(
            oracle,
            "_send_pulse_transaction",
            return_value={"success": False, "error": "tx_reverted"},
        ):
            result = await oracle.run_pulse_cycle(state, engine=engine)

        assert result["action"] == "PULSE_WITHHELD"


# ---------------------------------------------------------------------------
# Ledger persistence: SHA-256 integrity
# ---------------------------------------------------------------------------


class TestLedgerPersistence:
    @pytest.mark.asyncio
    async def test_sha256_in_meta(self) -> None:
        engine = _make_engine()
        oracle = OuroborosOracle()
        state = _make_state(test_failures=4)  # high entropy

        await oracle.run_pulse_cycle(state, engine=engine)

        meta = engine.store.call_args.kwargs.get("meta", {})
        digest = meta.get("payload_sha256", "")
        assert len(digest) == 64
        # Must be valid hex with the expected SHA-256 length
        assert int(digest, 16) >= 0

    @pytest.mark.asyncio
    async def test_no_engine_does_not_raise(self) -> None:
        oracle = OuroborosOracle()
        state = _make_state(test_failures=4)
        # Should complete without error even without an engine
        result = await oracle.run_pulse_cycle(state, engine=None)
        assert "action" in result

    @pytest.mark.asyncio
    async def test_ledger_failure_does_not_propagate(self) -> None:
        engine = _make_engine()
        engine.store = AsyncMock(side_effect=RuntimeError("ledger unavailable"))

        oracle = OuroborosOracle()
        state = _make_state(test_failures=4)
        # Oracle must survive ledger failures gracefully
        result = await oracle.run_pulse_cycle(state, engine=engine)
        assert result["action"] == "PULSE_WITHHELD"


# ---------------------------------------------------------------------------
# _send_pulse_transaction: web3 not installed
# ---------------------------------------------------------------------------


class TestSendPulseTransactionImportError:
    def test_returns_error_dict_when_web3_missing(self) -> None:
        oracle = OuroborosOracle(
            rpc_url="http://localhost:8545",
            private_key="0xdeadbeef",
            contract_address="0xCAFE",
        )
        with patch.dict("sys.modules", {"web3": None}):
            result = oracle._send_pulse_transaction()

        assert result["success"] is False
        assert "web3" in result["error"].lower()
