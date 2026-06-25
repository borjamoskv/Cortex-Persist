# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from click.testing import CliRunner

from legacy_research.cli import cli


def test_github_group_is_registered_on_root_cli() -> None:
    assert "github" in cli.commands


def test_github_help_lists_subcommands() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["github", "--help"])

    assert result.exit_code == 0
    assert "sync" in result.output
    assert "status" in result.output
