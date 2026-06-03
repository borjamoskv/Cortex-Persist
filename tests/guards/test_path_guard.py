import pytest
import logging
from pathlib import Path
from cortex.guards.path_guard import is_safe_path, resolve_and_verify


def test_is_safe_path_happy(tmp_path: Path):
    """Happy path: path is within base_dir."""
    base_dir = tmp_path
    safe_file = base_dir / "safe.txt"
    safe_file.touch()

    assert is_safe_path(safe_file, base_dir) is True


def test_is_safe_path_rejection(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Rejection path: path escapes base_dir."""
    base_dir = tmp_path / "workspace"
    base_dir.mkdir()

    unsafe_file = tmp_path / "unsafe.txt"
    unsafe_file.touch()

    with caplog.at_level(logging.WARNING):
        assert is_safe_path(unsafe_file, base_dir) is False

    assert "Blocked path traversal" in caplog.text


def test_is_safe_path_boundary(tmp_path: Path):
    """Boundary condition: exact base_dir and tricky path formats."""
    base_dir = tmp_path / "workspace"
    base_dir.mkdir()

    # Path with `..` that resolves inside
    tricky_inside = base_dir / "subdir" / ".." / "safe.txt"
    assert is_safe_path(tricky_inside, base_dir) is True

    # Path with `..` that escapes exactly one level above base_dir
    tricky_outside = base_dir / ".." / "unsafe.txt"
    assert is_safe_path(tricky_outside, base_dir) is False

    # Invalid path causing resolution error
    assert is_safe_path("\0", base_dir) is False


def test_resolve_and_verify_happy(tmp_path: Path):
    """Happy path: resolve valid path."""
    base_dir = tmp_path
    safe_file = base_dir / "safe.txt"
    safe_file.touch()

    resolved = resolve_and_verify(safe_file, base_dir)
    assert resolved == safe_file.resolve()


def test_resolve_and_verify_rejection(tmp_path: Path):
    """Rejection path: returns None for unsafe path."""
    base_dir = tmp_path / "workspace"
    base_dir.mkdir()

    unsafe_file = tmp_path / "unsafe.txt"
    unsafe_file.touch()

    resolved = resolve_and_verify(unsafe_file, base_dir)
    assert resolved is None


def test_resolve_and_verify_boundary(tmp_path: Path):
    """Boundary condition: current directory as default if base_dir is None."""
    # We can't strictly assert the CWD, but we can verify it resolves to a Path
    safe_file = Path.cwd() / "pyproject.toml"

    if safe_file.exists():
        resolved = resolve_and_verify(safe_file)
        assert resolved == safe_file.resolve()
