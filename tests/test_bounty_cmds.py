# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import pytest
from click.testing import CliRunner
from cortex.cli import cli

@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()

def test_bounty_hunt_logic_unsat(runner):
    """Test bounty hunt with direct logic formula that is contradictory."""
    result = runner.invoke(cli, ["bounty", "hunt", "--logic", "A & ~A"])
    assert result.exit_code == 0
    assert "Formula: A & ~A" in result.output
    assert "UNSAT" in result.output
    assert "Z3 Solver found contradiction" in result.output

def test_bounty_hunt_logic_sat(runner):
    """Test bounty hunt with direct logic formula that is satisfiable."""
    result = runner.invoke(cli, ["bounty", "hunt", "--logic", "A | ~A"])
    assert result.exit_code == 0
    assert "Formula: A | ~A" in result.output
    assert "SAT" in result.output

def test_bounty_hunt_logic_syntax_error(runner):
    """Test bounty hunt with invalid formula syntax."""
    # When logic fails parsing, it calls verify_rule and returns failure.
    # In direct logic execution, it will print the error message from z3_anvil.
    result = runner.invoke(cli, ["bounty", "hunt", "--logic", "A & & B"])
    assert result.exit_code == 0
    assert "Parsing error" in result.output
