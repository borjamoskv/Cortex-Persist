"""Tests for the AutoFixPipeline (Phase 2)."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from cortex.extensions.swarm.auto_fix import (
    AutoFixPipeline,
    GhostClass,
    GhostProtocol,
)


@dataclass
class MockGhost(GhostProtocol):
    id: str
    description: str
    project: str


def test_classify_ghosts():
    """Test O(1) pattern classification for different errors."""

    # 1. Code Bug
    assert (
        AutoFixPipeline.classify("TypeError: 'NoneType' object is not iterable")
        == GhostClass.CODE_BUG
    )
    assert AutoFixPipeline.classify("ValueError: invalid literal for int()") == GhostClass.CODE_BUG
    assert AutoFixPipeline.classify("ZeroDivisionError: division by zero") == GhostClass.CODE_BUG

    # 2. Config Error
    assert (
        AutoFixPipeline.classify("FileNotFoundError: [Errno 2] No such file")
        == GhostClass.CONFIG_ERROR
    )
    assert AutoFixPipeline.classify("Missing env var API_KEY") == GhostClass.CONFIG_ERROR

    # 3. Import Error
    assert (
        AutoFixPipeline.classify("ModuleNotFoundError: No module named 'cortex.foo'")
        == GhostClass.IMPORT_ERROR
    )
    assert (
        AutoFixPipeline.classify("ImportError: cannot import name 'X' from 'Y' (circular import)")
        == GhostClass.IMPORT_ERROR
    )

    # 4. Test Failure
    assert AutoFixPipeline.classify("AssertionError: assert False") == GhostClass.TEST_FAILURE
    assert (
        AutoFixPipeline.classify("FAILED tests/test_foo.py::test_bar - AssertionError")
        == GhostClass.TEST_FAILURE
    )

    # 5. Doc Gap
    assert AutoFixPipeline.classify("TODO: implement resilient retry") == GhostClass.DOC_GAP
    assert AutoFixPipeline.classify("FIXME: memory leak here") == GhostClass.DOC_GAP

    # 6. Unknown
    assert (
        AutoFixPipeline.classify("Something weird happened with the UI layout")
        == GhostClass.UNKNOWN
    )


def test_ghost_to_task():
    """Test that a ghost generates a valid AgentTask dict."""
    pipeline = AutoFixPipeline(repo_path="/testsuite/repo")

    ghost = MockGhost(id="ghost-123", description="TypeError in processing", project="TESTPROJ")

    classification = GhostClass.CODE_BUG
    task_dict = pipeline.ghost_to_task(
        ghost_id=ghost.id,
        description=ghost.description,
        classification=classification,
        project=ghost.project,
    )

    assert task_dict["id"] == "autofix-ghost-123"
    assert task_dict["repo_path"] == "/testsuite/repo"
    assert "TypeError in processing" in task_dict["description"]
    assert "ghost-123" in task_dict["description"]
    assert task_dict["source"] == "ghost"
    assert task_dict["title"] == "[AutoFix] code_bug: ghost #ghost-123"


@pytest.mark.asyncio
@patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._execute")
async def test_process_ghost_success(mock_execute):
    """Test standard successful autofix flow."""
    mock_execute.return_value = {
        "status": "done",
        "branch": "autofix/ghost-999",
        "summary": "Fixed the NoneType error",
        "error": "",
        "tests_passed": True,
    }

    pipeline = AutoFixPipeline()
    ghost = MockGhost(
        id="ghost-999",
        description="AttributeError: 'str' object has no attribute 'foo'",
        project="CORTEX",
    )

    result = await pipeline.process_ghost(ghost)

    assert result.success is True
    assert result.classification == GhostClass.CODE_BUG
    assert result.tests_passed is True
    assert result.branch == "autofix/ghost-999"
    assert result.ghost_id == "ghost-999"

    mock_execute.assert_called_once()


@pytest.mark.asyncio
@patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._execute")
@patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._escalate")
async def test_process_ghost_execution_failure(mock_escalate, mock_execute):
    """Test failure during Aether execution escalates the ghost (Ω₅)."""
    mock_execute.side_effect = RuntimeError("Aether crash: OOM")

    pipeline = AutoFixPipeline()
    ghost = MockGhost(
        id="ghost-fail", description="ImportError: No module named 'black'", project="CORTEX"
    )

    result = await pipeline.process_ghost(ghost)

    assert result.success is False
    assert result.classification == GhostClass.IMPORT_ERROR
    assert "Aether crash: OOM" in result.error
    assert result.ghost_id == "ghost-fail"

    mock_execute.assert_called_once()
    mock_escalate.assert_called_once_with(
        "ghost-fail", GhostClass.IMPORT_ERROR, "Aether crash: OOM", "CORTEX"
    )


@pytest.mark.asyncio
async def test_process_ghost_unknown_classification():
    """Test that unknown ghosts bypass Aether and fail cleanly."""
    pipeline = AutoFixPipeline()
    ghost = MockGhost(
        id="ghost-unk", description="The frontend button is blue instead of red.", project="CORTEX"
    )

    # _execute shouldn't even be called for UNKNOWN
    with patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._execute") as mock_exe:
        result = await pipeline.process_ghost(ghost)

        assert result.success is False
        assert result.classification == GhostClass.UNKNOWN
        mock_exe.assert_not_called()
