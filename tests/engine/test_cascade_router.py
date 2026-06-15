# [C5-REAL] Exergy-Maximized
"""
Unit tests for CascadeRouter routing logic.
"""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from cortex.engine.cascade_router import CascadeRouter


class TestCascadeRouter:
    """Test suite for the CascadeRouter class."""

    def test_select_engine_by_task_type(self):
        """Should select the correct engine based on task type heuristics."""
        router = CascadeRouter()

        # Architecture tasks should route to gemini
        assert router._select_engine("architecture", []) == "gemini"
        assert router._select_engine("deep_analysis", []) == "gemini"

        # Refactor/bugfix/general tasks should route to claude
        assert router._select_engine("refactor", []) == "claude"
        assert router._select_engine("bugfix", []) == "claude"
        assert router._select_engine("general", []) == "claude"

        # Snippet/test/quick tasks should route to codex
        assert router._select_engine("snippet", []) == "codex"
        assert router._select_engine("test", []) == "codex"

        # Unsupported task type fallback to claude
        assert router._select_engine("unknown_task", []) == "claude"

    def test_select_engine_by_file_count(self):
        """Should route to gemini if the number of files exceeds 5, regardless of task type."""
        router = CascadeRouter()

        # Snippet task with 6 files -> gemini (normally codex)
        assert router._select_engine("snippet", ["f1", "f2", "f3", "f4", "f5", "f6"]) == "gemini"

        # Refactor task with 6 files -> gemini (normally claude)
        assert router._select_engine("refactor", ["f1", "f2", "f3", "f4", "f5", "f6"]) == "gemini"

    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    @patch.dict("os.environ", {"CORTEX_LLM_LOCAL_FIRST": "1"})
    async def test_execute_gemini_with_files(self, mock_create):
        """Should call ollama qwen2.5-coder:32b when local_first is enabled."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Gemini Response", b""))
        mock_create.return_value = mock_process

        response = await router.route_task("Check this code", "architecture", ["app.py", "utils.py"])
        assert response == "Gemini Response"

        # Check call arguments
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        cmd = args
        assert cmd[:3] == ("ollama", "run", "qwen2.5-coder:32b")
        assert "Check this code" in cmd

    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    @patch.dict("os.environ", {"CORTEX_LLM_LOCAL_FIRST": "0"})
    async def test_execute_gemini_with_files_npx(self, mock_create):
        """Should call npx gemini-cli with file flags when local_first is disabled."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Gemini Response", b""))
        mock_create.return_value = mock_process

        response = await router.route_task("Check this code", "architecture", ["app.py", "utils.py"])
        assert response == "Gemini Response"

        mock_create.assert_called_once()
        cmd = mock_create.call_args[0]
        assert cmd[:3] == ("npx", "-y", "@google/gemini-cli")
        assert "--file" in cmd
        assert "app.py" in cmd
        assert "utils.py" in cmd
        assert "Check this code" in cmd

    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    @patch.dict("os.environ", {"CORTEX_LLM_LOCAL_FIRST": "1"})
    async def test_execute_claude(self, mock_create):
        """Should call ollama qwen2.5-coder:32b when local_first is enabled."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Claude Response", b""))
        mock_create.return_value = mock_process

        response = await router.route_task("Fix this typo", "refactor")
        assert response == "Claude Response"

        mock_create.assert_called_once()
        cmd = mock_create.call_args[0]
        assert cmd[:3] == ("ollama", "run", "qwen2.5-coder:32b")
        assert "Fix this typo" in cmd

    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    @patch.dict("os.environ", {"CORTEX_LLM_LOCAL_FIRST": "0"})
    async def test_execute_claude_npx(self, mock_create):
        """Should call npx claude-code when local_first is disabled."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Claude Response", b""))
        mock_create.return_value = mock_process

        response = await router.route_task("Fix this typo", "refactor")
        assert response == "Claude Response"

        mock_create.assert_called_once()
        cmd = mock_create.call_args[0]
        assert cmd[:3] == ("npx", "-y", "@anthropic-ai/claude-code")
        assert "Fix this typo" in cmd

    @patch("cortex.engine.cascade_router.asyncio.sleep")
    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    async def test_execute_timeout(self, mock_create, mock_sleep):
        """Should return timeout error message on subprocess timeout."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=[
            asyncio.TimeoutError(), (b"", b""),
            asyncio.TimeoutError(), (b"", b""),
            asyncio.TimeoutError(), (b"", b"")
        ])
        mock_process.kill = MagicMock()
        mock_create.return_value = mock_process

        response = await router.route_task("Generate large file", "snippet")
        assert "timed out" in response
        assert mock_create.call_count == 3

    @patch("cortex.engine.cascade_router.asyncio.sleep")
    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    async def test_execute_error_code(self, mock_create, mock_sleep):
        """Should return stderr error message on non-zero exit code."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"Some output", b"Permission Denied"))
        mock_create.return_value = mock_process

        response = await router.route_task("Run unauthorized command", "snippet")
        assert response == "Error (codex): Permission Denied"
        assert mock_create.call_count == 3

    @patch("cortex.engine.cascade_router.asyncio.sleep")
    @patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
    async def test_execute_file_not_found(self, mock_create, mock_sleep):
        """Should handle FileNotFoundError gracefully."""
        router = CascadeRouter()
        mock_create.side_effect = FileNotFoundError()

        # Let's see what happens when the executable is not found
        response = await router.route_task("Check this code", "snippet")
        assert "CLI tool" in response
        assert "not found in PATH" in response
