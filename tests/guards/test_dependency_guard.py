import pytest
from pathlib import Path
from cortex.guards.dependency_guard import scan_file, scan_directory


def test_scan_file_happy(tmp_path: Path):
    """Happy path: Scan file with no violations."""
    source_file = tmp_path / "clean.py"
    source_file.write_text("def my_func():\n    pass\n")

    violations = scan_file(source_file)
    assert len(violations) == 0


def test_scan_file_rejection(tmp_path: Path):
    """Rejection path: Scan file with oracle dependencies."""
    source_file = tmp_path / "violation.py"
    source_file.write_text("import subprocess\nsubprocess.run(['gpt-4'])\n")

    violations = scan_file(source_file)
    assert len(violations) > 0
    assert violations[0].binary == "gpt"


def test_scan_file_boundary(tmp_path: Path):
    """Boundary condition: File cannot be read (syntax error or missing)."""
    # Syntax error
    source_file = tmp_path / "syntax_err.py"
    source_file.write_text("def broken_syntax(\n")

    violations = scan_file(source_file)
    assert len(violations) == 0  # Ast parsing fails gracefully

    # Missing file
    violations = scan_file(tmp_path / "does_not_exist.py")
    assert len(violations) == 0


def test_scan_directory_happy(tmp_path: Path):
    """Happy path: Scan directory with only clean files."""
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "clean1.py").write_text("a = 1")
    (tmp_path / "dir" / "clean2.py").write_text("b = 2")

    violations = scan_directory(tmp_path)
    assert len(violations) == 0


def test_scan_directory_rejection(tmp_path: Path):
    """Rejection path: Scan directory containing files with violations."""
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "clean.py").write_text("a = 1")
    (tmp_path / "dir" / "violation.py").write_text("import os\nos.system('claude-3')")

    violations = scan_directory(tmp_path)
    assert len(violations) == 1
    assert violations[0].binary == "claude"
    assert "violation.py" in violations[0].file


def test_scan_directory_boundary(tmp_path: Path):
    """Boundary condition: Empty directory."""
    violations = scan_directory(tmp_path)
    assert len(violations) == 0
