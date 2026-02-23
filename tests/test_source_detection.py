"""Tests for agent source auto-detection in CLI store command."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from cortex.cli.core import _detect_agent_source


class TestDetectAgentSource:
    """Test _detect_agent_source priority chain."""

    def test_explicit_cortex_source_takes_priority(self):
        """CORTEX_SOURCE env var overrides everything."""
        with patch.dict(os.environ, {"CORTEX_SOURCE": "agent:custom-bot"}, clear=False):
            assert _detect_agent_source() == "agent:custom-bot"

    def test_explicit_overrides_agent_markers(self):
        """CORTEX_SOURCE takes priority over GEMINI_AGENT."""
        env = {"CORTEX_SOURCE": "agent:override", "GEMINI_AGENT": "true"}
        with patch.dict(os.environ, env, clear=False):
            assert _detect_agent_source() == "agent:override"

    def test_gemini_agent_detected(self):
        """GEMINI_AGENT env var maps to agent:gemini."""
        with patch.dict(os.environ, {"GEMINI_AGENT": "1"}, clear=False):
            os.environ.pop("CORTEX_SOURCE", None)
            assert _detect_agent_source() == "agent:gemini"

    def test_cursor_session_detected(self):
        """CURSOR_SESSION_ID env var maps to agent:cursor."""
        with patch.dict(os.environ, {"CURSOR_SESSION_ID": "abc123"}, clear=False):
            os.environ.pop("CORTEX_SOURCE", None)
            os.environ.pop("GEMINI_AGENT", None)
            assert _detect_agent_source() == "agent:cursor"

    def test_claude_code_detected(self):
        """CLAUDE_CODE_AGENT env var maps to agent:claude-code."""
        with patch.dict(os.environ, {"CLAUDE_CODE_AGENT": "1"}, clear=False):
            os.environ.pop("CORTEX_SOURCE", None)
            os.environ.pop("GEMINI_AGENT", None)
            os.environ.pop("CURSOR_SESSION_ID", None)
            assert _detect_agent_source() == "agent:claude-code"

    def test_kimi_session_detected(self):
        """KIMI_SESSION_ID env var maps to agent:kimi."""
        with patch.dict(os.environ, {"KIMI_SESSION_ID": "session-xyz"}, clear=False):
            os.environ.pop("CORTEX_SOURCE", None)
            os.environ.pop("GEMINI_AGENT", None)
            os.environ.pop("CURSOR_SESSION_ID", None)
            os.environ.pop("CLAUDE_CODE_AGENT", None)
            os.environ.pop("WINDSURF_SESSION", None)
            os.environ.pop("COPILOT_AGENT", None)
            assert _detect_agent_source() == "agent:kimi"

    def test_term_program_cursor_fallback(self):
        """TERM_PROGRAM containing 'cursor' maps to agent:cursor."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in {
                "CORTEX_SOURCE", "GEMINI_AGENT", "CURSOR_SESSION_ID",
                "CLAUDE_CODE_AGENT", "WINDSURF_SESSION", "COPILOT_AGENT",
                "KIMI_SESSION_ID",
            }
        }
        clean_env["TERM_PROGRAM"] = "cursor-terminal"
        with patch.dict(os.environ, clean_env, clear=True):
            assert _detect_agent_source() == "agent:cursor"

    def test_term_program_vscode_fallback(self):
        """TERM_PROGRAM containing 'vscode' maps to ide:vscode."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in {
                "CORTEX_SOURCE", "GEMINI_AGENT", "CURSOR_SESSION_ID",
                "CLAUDE_CODE_AGENT", "WINDSURF_SESSION", "COPILOT_AGENT",
                "KIMI_SESSION_ID",
            }
        }
        clean_env["TERM_PROGRAM"] = "vscode"
        with patch.dict(os.environ, clean_env, clear=True):
            assert _detect_agent_source() == "ide:vscode"

    def test_no_markers_returns_cli(self):
        """When no env markers present, returns 'cli'."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in {
                "CORTEX_SOURCE", "GEMINI_AGENT", "CURSOR_SESSION_ID",
                "CLAUDE_CODE_AGENT", "WINDSURF_SESSION", "COPILOT_AGENT",
                "KIMI_SESSION_ID", "TERM_PROGRAM",
            }
        }
        with patch.dict(os.environ, clean_env, clear=True):
            assert _detect_agent_source() == "cli"

    def test_empty_cortex_source_ignored(self):
        """Empty CORTEX_SOURCE string is treated as unset."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in {
                "CORTEX_SOURCE", "GEMINI_AGENT", "CURSOR_SESSION_ID",
                "CLAUDE_CODE_AGENT", "WINDSURF_SESSION", "COPILOT_AGENT",
                "KIMI_SESSION_ID", "TERM_PROGRAM",
            }
        }
        clean_env["CORTEX_SOURCE"] = ""
        with patch.dict(os.environ, clean_env, clear=True):
            # Empty string is falsy, should skip to fallback
            assert _detect_agent_source() == "cli"

    def test_return_type_is_string(self):
        """Always returns a non-empty string."""
        result = _detect_agent_source()
        assert isinstance(result, str)
        assert len(result) > 0
