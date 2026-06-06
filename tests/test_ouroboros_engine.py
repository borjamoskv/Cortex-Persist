# [C5-REAL] Exergy-Maximized
"""Tests for cortex-core/ouroboros_engine.py - Security Audit Engine.

C5-REAL coverage for provision, contract detection, test generation, and queue mechanisms.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import ouroboros_engine


class TestOuroborosEngine:
    @pytest.fixture
    def engine(self):
        engine = ouroboros_engine.OuroborosEngine(target_url="https://github.com/test/repo.git")
        engine.bus = MagicMock()
        engine._emit_event = AsyncMock()
        return engine

    @pytest.mark.asyncio
    async def test_provision(self, engine, tmp_path):
        ouroboros_engine.SCRATCH_BASE = str(tmp_path)
        await engine.provision()
        assert engine.scratch_dir is not None
        assert os.path.exists(engine.scratch_dir)
        assert "repo" in engine.scratch_dir

    @pytest.mark.asyncio
    async def test_clone_target(self, engine):
        engine.scratch_dir = "/tmp/fake_dir"
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_exec.return_value = mock_proc
            await engine.clone_target()
            mock_exec.assert_called_once_with(
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/test/repo.git",
                ".",
                cwd="/tmp/fake_dir",
            )
            mock_proc.wait.assert_awaited_once()

    def test_detect_contracts(self, engine, tmp_path):
        engine.scratch_dir = str(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "Vault.sol").write_text("contract Vault { }")
        (src / "Token.sol").write_text("contract MyToken is ERC20 { }")
        (src / "VaultTest.t.sol").write_text(
            "contract VaultTest { }"
        )  # Should be ignored (test in name)

        contracts = engine._detect_contracts()
        names = [c["name"] for c in contracts]
        assert len(contracts) == 2
        assert "Vault" in names
        assert "MyToken" in names
        assert "VaultTest" not in names

    @pytest.mark.asyncio
    async def test_generate_fuzz_test(self, engine, tmp_path):
        engine.scratch_dir = str(tmp_path)
        contract_file = str(tmp_path / "src" / "Vault.sol")
        test_file = await engine.generate_fuzz_test("Vault", contract_file)

        assert os.path.exists(test_file)
        content = open(test_file).read()
        assert "contract VaultOuroborosTest is Test" in content
        assert 'import "../src/Vault.sol"' in content
        assert "function test_FuzzExergy(uint256 amount)" in content

    def test_queue_remediation(self, engine, tmp_path):
        with patch("ouroboros_engine.time.time", return_value=12345):
            with patch("persistence.enqueue_swarm_task") as mock_enqueue:
                engine._queue_remediation("/target/file.sol", "/target/error.log")
                mock_enqueue.assert_called_once()
                args, kwargs = mock_enqueue.call_args
                assert args[0] == "SURGEON-1"
                assert args[1]["type"] == "remediation"
                assert "/target/file.sol" in args[1]["command"]
