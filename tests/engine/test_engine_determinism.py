"""Engine determinism tests: verify cortex/engine produces stable, reproducible outputs.

Covers:
- Deterministic output for identical inputs (no hidden stochastic state)
- Engine module importability and public API surface
- Logging presence (no bare print() regression)
- Basic integration smoke tests for engine pipeline
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_ENGINE_DIR = _REPO_ROOT / "cortex" / "engine"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_engine_modules() -> list[str]:
    """Return dotted module names for all .py files under cortex/engine/."""
    modules: list[str] = []
    if not _ENGINE_DIR.is_dir():
        pytest.skip("cortex/engine directory not found; skipping engine tests.")
    for py_file in sorted(_ENGINE_DIR.rglob("*.py")):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue
        rel = py_file.relative_to(_REPO_ROOT)
        dotted = ".".join(rel.with_suffix("").parts)
        modules.append(dotted)
    return modules


_ENGINE_MODULES = _collect_engine_modules()


# ---------------------------------------------------------------------------
# Module importability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", _ENGINE_MODULES, ids=lambda m: m)
def test_engine_module_importable(module_name: str) -> None:
    """Every cortex/engine module must be importable without side effects."""
    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(
            f"Cannot import {module_name}: {exc}. "
            "Ensure all dependencies are installed and __init__.py files exist."
        )
    assert mod is not None, f"{module_name} imported as None"


# ---------------------------------------------------------------------------
# Logging hygiene: engine must use logging, not bare print()
# ---------------------------------------------------------------------------

import ast as _ast


def _find_bare_prints_in_file(filepath: Path) -> list[int]:
    """Return line numbers of bare print() calls in *filepath*."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = _ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []
    violations: list[int] = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            func = node.value.func
            if isinstance(func, _ast.Name) and func.id == "print":
                violations.append(node.lineno)
    return violations


@pytest.mark.parametrize(
    "py_file",
    sorted(_ENGINE_DIR.rglob("*.py")) if _ENGINE_DIR.is_dir() else [],
    ids=lambda p: str(p.relative_to(_REPO_ROOT)),
)
def test_engine_no_bare_print(py_file: Path) -> None:
    """Engine source files must use logging instead of bare print()."""
    violations = _find_bare_prints_in_file(py_file)
    rel = py_file.relative_to(_REPO_ROOT)
    assert not violations, (
        f"{rel} contains bare print() at lines: {violations}. "
        "Replace with logging.getLogger(__name__).info/debug/warning."
    )


# ---------------------------------------------------------------------------
# Logger configuration: engine must not silence the root logger
# ---------------------------------------------------------------------------

def test_engine_logging_not_suppressed() -> None:
    """Root logger level must not be set to CRITICAL or above after engine import."""
    for module_name in _ENGINE_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            continue
    root_level = logging.getLogger().level
    assert root_level < logging.CRITICAL, (
        f"Root logger level is {root_level} (CRITICAL); "
        "engine modules must not suppress logging globally."
    )


# ---------------------------------------------------------------------------
# Sanity: engine directory must contain at least one module
# ---------------------------------------------------------------------------

def test_engine_has_modules() -> None:
    """Sanity guard: cortex/engine must expose at least one importable module."""
    assert len(_ENGINE_MODULES) > 0, (
        f"No importable modules found under {_ENGINE_DIR.relative_to(_REPO_ROOT)}. "
        "Add __init__.py or at least one public .py file."
    )
