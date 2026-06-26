from __future__ import annotations
# [C5-REAL] Exergy-Maximized
import pytest
pytestmark = pytest.mark.integration


import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex_extensions.llm.provider import LLMProvider
from cortex_extensions.llm.vllm_edge import NativeVLLMProvider
from cortex_extensions.training.daemon import AutonomousTrainingDaemon
from cortex_extensions.training.verifier import AdapterVerifier


@pytest.fixture
def mock_home(tmp_path, monkeypatch):
    """Patches Path.home() to return a temporary directory to isolate test state."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


class TestAdapterVerifier:
    def test_verify_adapter_missing_dir(self, mock_home) -> None:
        verifier = AdapterVerifier()
        result = verifier.verify_adapter(mock_home / "nonexistent", "base-model")
        assert not result["success"]
        assert "does not exist or is not a directory" in result["error"]

    def test_verify_adapter_missing_config(self, mock_home) -> None:
        adapter_dir = mock_home / "adapter"
        adapter_dir.mkdir()
        verifier = AdapterVerifier()
        result = verifier.verify_adapter(adapter_dir, "base-model")
        assert not result["success"]
        assert "Missing 'adapter_config.json'" in result["error"]

    def test_verify_adapter_missing_weights(self, mock_home) -> None:
        adapter_dir = mock_home / "adapter"
        adapter_dir.mkdir()
        config_file = adapter_dir / "adapter_config.json"
        config_file.write_text(json.dumps({"model": "base-model"}))

        verifier = AdapterVerifier()
        result = verifier.verify_adapter(adapter_dir, "base-model")
        assert not result["success"]
        assert "Missing weights file" in result["error"]

    def test_verify_adapter_success_npz(self, mock_home) -> None:
        adapter_dir = mock_home / "adapter"
        adapter_dir.mkdir()
        config_file = adapter_dir / "adapter_config.json"
        config_file.write_text(
            json.dumps({"model": "base-model", "validation_loss": 0.12, "iters": 100})
        )
        weights_npz = adapter_dir / "weights.npz"
        weights_npz.write_text("fake weights")

        verifier = AdapterVerifier()
        result = verifier.verify_adapter(adapter_dir, "base-model")
        assert result["success"]
        assert result["safety_status"] == "PASSED"
        assert result["metrics"]["validation_loss"] == 0.12
        assert result["metrics"]["iters"] == 100

    def test_verify_adapter_success_safetensors(self, mock_home) -> None:
        adapter_dir = mock_home / "adapter"
        adapter_dir.mkdir()
        config_file = adapter_dir / "adapter_config.json"
        config_file.write_text(
            json.dumps({"model": "base-model", "validation_loss": 0.05, "iters": 200})
        )
        weights_safetensors = adapter_dir / "adapters.safetensors"
        weights_safetensors.write_text("fake safetensors weights")

        verifier = AdapterVerifier()
        result = verifier.verify_adapter(adapter_dir, "base-model")
        assert result["success"]
        assert result["metrics"]["validation_loss"] == 0.05
        assert result["metrics"]["iters"] == 200


class TestAutonomousTrainingDaemon:
    @pytest.mark.asyncio
    async def test_get_all_session_ids(self, mock_home) -> None:
        mock_episodic_memory = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [("session-1",), ("session-2",), (None,)]

        # Context manager simulation for fetchall
        mock_conn.execute.return_value.__aenter__.return_value = mock_cursor
        mock_episodic_memory._conn = mock_conn

        daemon = AutonomousTrainingDaemon(mock_episodic_memory)
        session_ids = await daemon.get_all_session_ids()
        assert session_ids == ["session-1", "session-2"]

    @pytest.mark.asyncio
    @patch(
        "cortex_extensions.training.ttt_engine.TTTEngine.run_nocturnal_consolidation",
        new_callable=AsyncMock,
    )
    async def test_run_cycle_success(self, mock_consolidate, mock_home) -> None:
        mock_episodic_memory = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [("session-1",), ("session-2",)]
        mock_conn.execute.return_value.__aenter__.return_value = mock_cursor
        mock_episodic_memory._conn = mock_conn

        # Create mock adapter output path in tmp_path
        adapter_dir = mock_home / "adapter"
        adapter_dir.mkdir()
        config_file = adapter_dir / "adapter_config.json"
        config_file.write_text(
            json.dumps({"model": "base-model", "validation_loss": 0.08, "iters": 150})
        )
        weights_npz = adapter_dir / "weights.npz"
        weights_npz.write_text("fake weights")

        mock_consolidate.return_value = {
            "status": "success",
            "average_reward": 0.85,
            "golden_trajectories": 2,
        }

        daemon = AutonomousTrainingDaemon(mock_episodic_memory, base_model="base-model")
        # Overwrite adapter path to return our mock dir
        daemon.ttt_engine.adapter_path = adapter_dir

        result = await daemon.run_cycle()
        assert result["status"] == "success"
        assert result["processed_sessions"] == 2
        assert result["metrics"]["average_reward"] == 0.85

        # Verify registry file created and has correct format
        registry_file = mock_home / ".cortex" / "training" / "verified_adapter.json"
        assert registry_file.exists()
        with open(registry_file, encoding="utf-8") as f:
            reg = json.load(f)
            assert reg["status"] == "verified"
            assert reg["base_model"] == "base-model"
            assert reg["adapter_path"] == str(adapter_dir.resolve())

        # Verify consolidation tracking saved
        consolidated_file = mock_home / ".cortex" / "training" / "consolidated_sessions.json"
        assert consolidated_file.exists()
        with open(consolidated_file, encoding="utf-8") as f:
            sessions = json.load(f)
            assert set(sessions) == {"session-1", "session-2"}

    @pytest.mark.asyncio
    @patch(
        "cortex_extensions.training.ttt_engine.TTTEngine.run_nocturnal_consolidation",
        new_callable=AsyncMock,
    )
    async def test_run_cycle_skipped(self, mock_consolidate, mock_home) -> None:
        mock_episodic_memory = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [("session-1",)]
        mock_conn.execute.return_value.__aenter__.return_value = mock_cursor
        mock_episodic_memory._conn = mock_conn

        mock_consolidate.return_value = {
            "status": "skipped",
            "reason": "No high-reward data",
        }

        daemon = AutonomousTrainingDaemon(mock_episodic_memory)
        result = await daemon.run_cycle()
        assert result["status"] == "skipped"
        assert result["reason"] == "No high-reward data"
        assert result["processed_sessions"] == 1

        # Check marked as consolidated
        consolidated_file = mock_home / ".cortex" / "training" / "consolidated_sessions.json"
        assert consolidated_file.exists()

    @pytest.mark.asyncio
    async def test_daemon_loop_lifecycle(self, mock_home) -> None:
        mock_episodic_memory = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value.__aenter__.return_value = mock_cursor
        mock_episodic_memory._conn = mock_conn

        daemon = AutonomousTrainingDaemon(mock_episodic_memory, interval_seconds=1)
        await daemon.start()
        assert daemon.is_running
        assert daemon._task is not None

        await asyncio.sleep(0.1)
        await daemon.stop()
        assert not daemon.is_running


class TestLLMProviderLoRARouting:
    @patch("cortex_extensions.llm.provider.load_presets")
    @pytest.mark.asyncio
    async def test_vllm_routes_to_adapter_when_verified(self, mock_load_presets, mock_home) -> None:
        mock_presets = {
            "vllm": {
                "base_url": "http://localhost:8000/v1",
                "default_model": "local-model",
                "tier": "local",
                "cost_class": "free",
                "specialization": ["general"],
            }
        }
        mock_load_presets.return_value = mock_presets

        # 1. Without verified adapter registry
        provider = LLMProvider(provider="vllm")
        from cortex_extensions.llm._models import IntentProfile

        resolved_model = provider._resolve_model(IntentProfile.GENERAL)
        assert resolved_model == "local-model"

        # 2. Register a verified adapter
        registry_dir = mock_home / ".cortex" / "training"
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / "verified_adapter.json"
        registry_file.write_text(
            json.dumps(
                {
                    "adapter_path": "/path/to/my/awesome_lora_adapter",
                    "status": "verified",
                }
            )
        )

        # Re-resolve and verify path is returned
        resolved_model_lora = provider._resolve_model(IntentProfile.GENERAL)
        assert resolved_model_lora == "/path/to/my/awesome_lora_adapter"

    @pytest.mark.asyncio
    async def test_native_vllm_adapter_loading_simulation(self, mock_home) -> None:
        # Patch import of vllm to prevent failures on non-VRAM systems
        mock_vllm = MagicMock()
        mock_args = MagicMock()
        mock_engine = MagicMock()
        mock_vllm.AsyncEngineArgs = mock_args
        mock_vllm.AsyncLLMEngine.from_engine_args.return_value = mock_engine

        # Mock the entire vllm module import
        with patch.dict("sys.modules", {"vllm": mock_vllm}):
            # Setup verified adapter
            registry_dir = mock_home / ".cortex" / "training"
            registry_dir.mkdir(parents=True, exist_ok=True)
            registry_file = registry_dir / "verified_adapter.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "adapter_path": "/path/to/my/awesome_lora_adapter",
                        "status": "verified",
                    }
                )
            )

            # Instantiation will read the registry file and should load LoRA config
            provider = NativeVLLMProvider()
            assert provider.provider_name == "vllm_native"
            mock_args.assert_called_once()
            kwargs = mock_args.call_args[1]
            assert kwargs["enable_lora"] is True
            assert kwargs["max_loras"] == 4
