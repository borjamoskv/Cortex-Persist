# [C5-REAL] Exergy-Maximized
import pytest
from cortex.engine.cascade_router import CascadeRouter


def test_select_engine():
    router = CascadeRouter()

    # Architecture with many files -> gemini
    assert router._select_engine("architecture", ["f1", "f2", "f3", "f4", "f5", "f6"]) == "gemini"
    assert router._select_engine("audit", []) == "gemini"

    # Refactor -> claude
    assert router._select_engine("refactor", ["f1"]) == "claude"
    assert router._select_engine("bugfix", []) == "claude"

    # Quick/test -> codex
    assert router._select_engine("snippet", []) == "codex"
    assert router._select_engine("test", []) == "codex"


def test_fallback_response():
    router = CascadeRouter()
    response = router.fallback_response("gemini", "test prompt")
    assert "not found in PATH" in response
    assert "gemini" in response


from unittest.mock import patch


@patch("cortex.engine.cascade_router.asyncio.create_subprocess_exec")
def test_route_task_fallback(mock_create_exec):
    import asyncio

    mock_create_exec.side_effect = FileNotFoundError()
    router = CascadeRouter()
    # Since we mocked FileNotFoundError, this will trigger fallback_response
    response = asyncio.run(router.route_task("test prompt", task_type="snippet"))
    assert "not found in PATH" in response
    assert "codex" in response
