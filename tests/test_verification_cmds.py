# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import pytest
from click.testing import CliRunner
from babylon60.cli import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def test_verify_files_no_args(runner):
    """Test verification CLI with no files specified."""
    result = runner.invoke(cli, ["verify-files"])
    assert result.exit_code == 0
    assert "No se especificaron archivos para verificar." in result.output


def test_verify_files_success(runner, tmp_path):
    """Test verification CLI with a valid Python file."""
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("# Clear file\nprint('Hello world')\n", encoding="utf-8")

    result = runner.invoke(cli, ["verify-files", str(valid_file)])
    assert result.exit_code == 0
    assert "PASSED" in result.output
    assert "FORMAL VERIFICATION COMPLETED SUCCESSFULLY" in result.output


def test_verify_files_failure_eval(runner, tmp_path):
    """Test verification CLI with an invalid Python file violating I7 (eval)."""
    invalid_file = tmp_path / "invalid_eval.py"
    invalid_file.write_text("eval('import os; os.system(\"rm -rf /\")')\n", encoding="utf-8")

    result = runner.invoke(cli, ["verify-files", str(invalid_file)])
    assert result.exit_code == 1
    assert "FAILED" in result.output
    assert "Prohibited use of 'eval'" in result.output
    assert "prevents termination analysis" in result.output
    assert "FORMAL VERIFICATION FAILED. Blocking integration." in result.output


def test_verify_files_failure_delete(runner, tmp_path):
    """Test verification CLI with an invalid Python file violating I2 (delete)."""
    invalid_file = tmp_path / "invalid_delete.py"
    invalid_file.write_text(
        "class Foo:\n    def delete(self):\n        pass\n\nf = Foo()\nf.delete()\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["verify-files", str(invalid_file)])
    assert result.exit_code == 1
    assert "FAILED" in result.output
    assert "Prohibited method call" in result.output
    assert "delete" in result.output
    assert "FORMAL VERIFICATION FAILED. Blocking integration." in result.output


def test_verify_files_syntax_error(runner, tmp_path):
    """Test verification CLI with a Python file containing syntax errors."""
    invalid_file = tmp_path / "invalid_syntax.py"
    invalid_file.write_text("this is not python code\n", encoding="utf-8")

    result = runner.invoke(cli, ["verify-files", str(invalid_file)])
    assert result.exit_code == 1
    assert "FAILED" in result.output
    assert "Code parsing failed" in result.output
    assert "FORMAL VERIFICATION FAILED. Blocking integration." in result.output
