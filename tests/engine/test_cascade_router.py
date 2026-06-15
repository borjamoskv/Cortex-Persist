# [C5-REAL] Exergy-Maximized
"""
Unit tests for CascadeRouter routing logic.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

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

    @patch("cortex.engine.cascade_router.subprocess.run")
    def test_execute_gemini_with_files(self, mock_run):
        """Should call npx @google/gemini-cli with file flags."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Gemini Response"
        mock_run.return_value = mock_process

        response = router.route_task("Check this code", "architecture", ["app.py", "utils.py"])
        assert response == "Gemini Response"

        # Check call arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[:3] == ["npx", "-y", "@google/gemini-cli"]
        assert "--file" in cmd
        assert "app.py" in cmd
        assert "utils.py" in cmd
        assert "Check this code" in cmd

    @patch("cortex.engine.cascade_router.subprocess.run")
    def test_execute_claude(self, mock_run):
        """Should call npx @anthropic-ai/claude-code."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Claude Response"
        mock_run.return_value = mock_process

        response = router.route_task("Fix this typo", "refactor")
        assert response == "Claude Response"

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["npx", "-y", "@anthropic-ai/claude-code"]
        assert "Fix this typo" in cmd

    @patch("cortex.engine.cascade_router.subprocess.run")
    def test_execute_timeout(self, mock_run):
        """Should return timeout error message on subprocess timeout."""
        router = CascadeRouter()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["codex"], timeout=300)

        response = router.route_task("Generate large file", "snippet")
        assert "timed out" in response

    @patch("cortex.engine.cascade_router.subprocess.run")
    def test_execute_error_code(self, mock_run):
        """Should return stderr error message on non-zero exit code."""
        router = CascadeRouter()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Permission Denied"
        mock_run.return_value = mock_process

        response = router.route_task("Run unauthorized command", "snippet")
        assert "Error" in response
        assert "Permission Denied" in response
