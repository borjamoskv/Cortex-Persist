"""Tests for CORTEX Agent Built-in Tools.

Tests:
    - FileReadTool: reads file contents, supports line ranges
    - FileWriteTool: writes files, creates directories
    - TerminalTool: executes commands, enforces timeout
    - GitTool: git status
"""

from __future__ import annotations

import pytest

from cortex.agents.agent_tools import (
    FileReadTool,
    FileWriteTool,
    GitTool,
    TerminalTool,
    TestRunnerTool,
    register_builtin_tools,
)
from cortex.agents.tools import ToolRegistry


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        tool = FileReadTool(workdir=str(tmp_path))
        result = await tool.execute(path=str(test_file))

        assert result["content"] == "line1\nline2\nline3\n"
        assert result["path"] == str(test_file)

    @pytest.mark.asyncio
    async def test_read_line_range(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\nline4\n")

        tool = FileReadTool(workdir=str(tmp_path))
        result = await tool.execute(
            path=str(test_file), start_line=2, end_line=3,
        )

        assert "line2" in result["content"]
        assert "line3" in result["content"]
        assert "line1" not in result["content"]

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tmp_path):
        tool = FileReadTool(workdir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            await tool.execute(path=str(tmp_path / "nope.txt"))

    @pytest.mark.asyncio
    async def test_path_validation(self, tmp_path):
        tool = FileReadTool(workdir=str(tmp_path))
        with pytest.raises(PermissionError):
            await tool.execute(path="/etc/passwd")

    def test_tool_name(self):
        assert FileReadTool().name == "file_read"


class TestFileWriteTool:
    @pytest.mark.asyncio
    async def test_write_file(self, tmp_path):
        tool = FileWriteTool(workdir=str(tmp_path))
        result = await tool.execute(
            path=str(tmp_path / "output.txt"),
            content="hello world",
        )

        assert result["created"] is True
        assert result["bytes_written"] == 11
        assert (tmp_path / "output.txt").read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_dirs(self, tmp_path):
        tool = FileWriteTool(workdir=str(tmp_path))
        nested = tmp_path / "a" / "b" / "c" / "file.txt"
        await tool.execute(path=str(nested), content="deep")

        assert nested.read_text() == "deep"

    @pytest.mark.asyncio
    async def test_path_required(self, tmp_path):
        tool = FileWriteTool(workdir=str(tmp_path))
        with pytest.raises(ValueError, match="path"):
            await tool.execute(content="no path given")

    def test_tool_name(self):
        assert FileWriteTool().name == "file_write"


class TestTerminalTool:
    @pytest.mark.asyncio
    async def test_echo(self, tmp_path):
        tool = TerminalTool(workdir=str(tmp_path))
        result = await tool.execute(command="echo hello")

        assert result["success"] is True
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_failing_command(self, tmp_path):
        tool = TerminalTool(workdir=str(tmp_path))
        result = await tool.execute(command="exit 1")

        assert result["success"] is False
        assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_timeout(self, tmp_path):
        tool = TerminalTool(workdir=str(tmp_path), timeout=0.5)
        with pytest.raises(TimeoutError):
            await tool.execute(command="sleep 10")

    @pytest.mark.asyncio
    async def test_command_required(self, tmp_path):
        tool = TerminalTool(workdir=str(tmp_path))
        with pytest.raises(ValueError, match="command"):
            await tool.execute()

    def test_tool_name(self):
        assert TerminalTool().name == "terminal"


class TestGitTool:
    @pytest.mark.asyncio
    async def test_status(self, tmp_path):
        # Init a git repo in tmp_path
        import subprocess

        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True,
        )

        tool = GitTool(workdir=str(tmp_path))
        result = await tool.execute(action="status")

        assert result["action"] == "status"
        assert "clean" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tmp_path):
        tool = GitTool(workdir=str(tmp_path))
        with pytest.raises(ValueError, match="Unknown git action"):
            await tool.execute(action="rebase_interactive")

    def test_tool_name(self):
        assert GitTool().name == "git"


class TestTestRunnerTool:
    def test_tool_name(self):
        assert TestRunnerTool().name == "test_runner"


class TestRegisterBuiltinTools:
    def test_registers_all_tools(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)

        expected = {"file_read", "file_write", "terminal", "test_runner", "git"}
        registered = set(registry.list_tools())
        assert expected == registered

    def test_registers_with_workdir(self, tmp_path):
        registry = ToolRegistry()
        register_builtin_tools(registry, workdir=str(tmp_path))
        assert len(registry) == 5
