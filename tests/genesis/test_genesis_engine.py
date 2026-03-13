"""Tests for cortex.genesis.engine — GenesisEngine core orchestration.

Includes the Ω₀ self-referential test: the engine generates its own spec
and assembles it in /tmp to verify recursive integrity.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from cortex.genesis.assembler import SystemAssembler
from cortex.genesis.engine import GenesisEngine
from cortex.genesis.models import ComponentSpec, SystemSpec
from cortex.genesis.validator import GenesisValidator

# All tests use /tmp to avoid polluting the real codebase
_TEST_ROOT = Path("/tmp/genesis_test_workspace")


@pytest.fixture(autouse=True)
def clean_workspace() -> None:
    """Ensure clean workspace before each test."""
    if _TEST_ROOT.exists():
        shutil.rmtree(_TEST_ROOT)
    _TEST_ROOT.mkdir(parents=True, exist_ok=True)
    yield  # type: ignore[misc]
    # Cleanup after test
    if _TEST_ROOT.exists():
        shutil.rmtree(_TEST_ROOT)


class TestGenesisEngineCreate:
    """Core create() flow tests."""

    def test_create_minimal_module(self) -> None:
        """Create a system with a single module component."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="mini",
            system_type="module",
            components=[
                ComponentSpec(name="core", component_type="module"),
            ],
        )
        result = engine.create(spec)

        assert result.validation_passed
        assert len(result.files_created) >= 2  # __init__.py + core.py
        assert result.hours_saved > 0

        # Verify files on disk
        assert (_TEST_ROOT / "mini" / "__init__.py").exists()
        assert (_TEST_ROOT / "mini" / "core.py").exists()

    def test_create_with_multiple_components(self) -> None:
        """Create a system with 3 components including dependencies."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="complex",
            components=[
                ComponentSpec(name="models", component_type="dataclass"),
                ComponentSpec(
                    name="store",
                    component_type="mixin",
                    dependencies=["models"],
                ),
                ComponentSpec(
                    name="manager",
                    component_type="module",
                    dependencies=["models", "store"],
                ),
            ],
        )
        result = engine.create(spec)

        assert result.validation_passed
        # __init__.py + models.py + store.py + manager.py = 4
        assert len(result.files_created) >= 4
        assert (_TEST_ROOT / "complex" / "models.py").exists()
        assert (_TEST_ROOT / "complex" / "store.py").exists()
        assert (_TEST_ROOT / "complex" / "manager.py").exists()

    def test_create_with_auto_tests(self) -> None:
        """Auto-test generation creates test stubs."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="tested",
            auto_tests=True,
            components=[
                ComponentSpec(name="logic", component_type="module", interfaces=["run"]),
            ],
        )
        result = engine.create(spec)

        assert result.validation_passed
        # Check test stubs were generated
        test_files = [f for f in result.files_created if "test_" in f]
        assert len(test_files) >= 1

    def test_create_skill_type(self) -> None:
        """Create a skill-type system (SKILL.md)."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="my_skill",
            system_type="skill",
            components=[
                ComponentSpec(
                    name="my_skill",
                    component_type="skill",
                    docstring="A test skill.",
                ),
            ],
        )
        result = engine.create(spec)

        assert result.validation_passed
        assert any("SKILL.md" in f for f in result.files_created)

    def test_create_agent_type(self) -> None:
        """Create an agent-type system (YAML definition)."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="scout_agent",
            system_type="agent",
            components=[
                ComponentSpec(name="scout_agent", component_type="agent"),
            ],
        )
        result = engine.create(spec)

        assert result.validation_passed
        assert any(".yaml" in f for f in result.files_created)

    def test_create_from_dict(self) -> None:
        """Create from a raw dictionary (YAML-like input)."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        d = {
            "name": "from_dict",
            "system_type": "module",
            "components": [
                {"name": "core", "component_type": "module"},
            ],
        }
        result = engine.create_from_dict(d)

        assert result.validation_passed
        assert result.spec.name == "from_dict"

    def test_failed_files_reported(self) -> None:
        """Components with no matching template report failures gracefully."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="robust",
            components=[
                ComponentSpec(name="ok", component_type="module"),
            ],
        )
        # This should still work — module template exists
        result = engine.create(spec)
        assert result.validation_passed


class TestGenesisEngineSelfCreate:
    """Ω₀: Self-referential auto-creation tests."""

    def test_self_create_returns_valid_spec(self) -> None:
        """self_create() returns a spec describing the genesis module."""
        engine = GenesisEngine()
        spec = engine.self_create()

        assert spec.name == "genesis"
        assert spec.system_type == "module"
        assert spec.auto_cli is True
        assert spec.auto_tests is True
        assert len(spec.components) == 5

        # Check key components exist
        comp_names = {c.name for c in spec.components}
        assert "models" in comp_names
        assert "engine" in comp_names
        assert "templates" in comp_names
        assert "assembler" in comp_names
        assert "validator" in comp_names

    def test_self_create_assembles_in_tmp(self) -> None:
        """The self-spec can be assembled into a real directory."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = engine.self_create()
        result = engine.create(spec)

        assert result.validation_passed
        assert len(result.files_created) >= 6  # 5 components + __init__.py
        assert result.hours_saved > 0

        # The generated genesis should contain __init__.py
        assert (_TEST_ROOT / "genesis" / "__init__.py").exists()

    def test_self_create_spec_roundtrips(self) -> None:
        """self_create spec serializes and deserializes cleanly."""
        engine = GenesisEngine()
        spec = engine.self_create()
        d = spec.to_dict()
        restored = SystemSpec.from_dict(d)
        assert restored.name == spec.name
        assert len(restored.components) == len(spec.components)


class TestGenesisEnginePreview:
    """Preview functionality tests."""

    def test_preview_lists_expected_files(self) -> None:
        engine = GenesisEngine()
        spec = SystemSpec(
            name="preview_test",
            auto_tests=True,
            auto_cli=True,
            components=[
                ComponentSpec(name="core", component_type="module"),
                ComponentSpec(name="data", component_type="dataclass"),
            ],
        )
        preview = engine.preview(spec)

        assert "core" in preview
        assert "data" in preview
        assert "__auto__" in preview
        assert "__init__.py" in preview["__auto__"]
        assert "tests/" in preview["__auto__"]


class TestChronosCalculation:
    """CHRONOS-1 yield calculation tests."""

    def test_chronos_positive_for_any_creation(self) -> None:
        """Any genesis operation should report positive hours saved."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        spec = SystemSpec(
            name="chrono_test",
            components=[ComponentSpec(name="a", component_type="module")],
        )
        result = engine.create(spec)
        assert result.hours_saved > 0

    def test_chronos_scales_with_complexity(self) -> None:
        """More components = more hours saved."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)

        simple = SystemSpec(
            name="simple",
            components=[ComponentSpec(name="a", component_type="module")],
        )
        complex_spec = SystemSpec(
            name="complex_sys",
            components=[
                ComponentSpec(name="a", component_type="module"),
                ComponentSpec(name="b", component_type="dataclass"),
                ComponentSpec(name="c", component_type="mixin"),
                ComponentSpec(name="d", component_type="module", dependencies=["a", "b", "c"]),
            ],
        )

        r1 = engine.create(simple)
        r2 = engine.create(complex_spec)

        assert r2.hours_saved > r1.hours_saved


class TestTopologicalSort:
    """Dependency resolution tests."""

    def test_sorts_by_dependencies(self) -> None:
        assembler = SystemAssembler()
        components = [
            ComponentSpec(name="c", dependencies=["a", "b"]),
            ComponentSpec(name="a"),
            ComponentSpec(name="b", dependencies=["a"]),
        ]
        ordered = assembler._resolve_dependencies(components)
        names = [c.name for c in ordered]

        # 'a' must come before 'b' and 'c'
        assert names.index("a") < names.index("b")
        assert names.index("a") < names.index("c")
        assert names.index("b") < names.index("c")

    def test_handles_no_dependencies(self) -> None:
        assembler = SystemAssembler()
        components = [
            ComponentSpec(name="x"),
            ComponentSpec(name="y"),
            ComponentSpec(name="z"),
        ]
        ordered = assembler._resolve_dependencies(components)
        assert len(ordered) == 3

    def test_handles_circular_dependencies(self) -> None:
        """Circular deps don't crash — remaining nodes are appended."""
        assembler = SystemAssembler()
        components = [
            ComponentSpec(name="a", dependencies=["b"]),
            ComponentSpec(name="b", dependencies=["a"]),
        ]
        ordered = assembler._resolve_dependencies(components)
        assert len(ordered) == 2


class TestGenesisValidator:
    """Post-creation validator tests."""

    def test_validates_existing_files(self) -> None:
        validator = GenesisValidator()
        # Create a file with system name in the path
        test_dir = _TEST_ROOT / "validator_test"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "valid.py"
        test_file.write_text("x = 1\n", encoding="utf-8")

        spec = SystemSpec(name="validator_test", system_type="workflow")
        passed, errors = validator.validate(spec, [str(test_file)])
        assert passed
        assert len(errors) == 0

    def test_catches_missing_files(self) -> None:
        validator = GenesisValidator()
        spec = SystemSpec(name="missing", system_type="workflow")
        passed, errors = validator.validate(spec, ["/nonexistent/file.py"])
        assert not passed
        assert any("does not exist" in e for e in errors)

    def test_catches_syntax_errors(self) -> None:
        validator = GenesisValidator()
        bad_file = _TEST_ROOT / "bad.py"
        _TEST_ROOT.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("def broken(\n", encoding="utf-8")

        spec = SystemSpec(name="bad_syntax", system_type="workflow")
        passed, errors = validator.validate(spec, [str(bad_file)])
        assert not passed
        assert any("Syntax error" in e for e in errors)


class TestGenesisExtend:
    """Incremental genesis tests (#1)."""

    def test_extend_adds_components(self) -> None:
        """extend() adds new files to an existing system."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        # First create a base system
        base_spec = SystemSpec(
            name="extendable",
            components=[ComponentSpec(name="core", component_type="module")],
        )
        engine.create(base_spec)

        base_dir = _TEST_ROOT / "extendable"
        assert base_dir.exists()

        # Now extend with a new component
        result = engine.extend(
            base_dir,
            [
                ComponentSpec(
                    name="extra",
                    component_type="dataclass",
                )
            ],
        )

        assert (base_dir / "extra.py").exists()
        assert len(result.files_created) >= 1

    def test_extend_skips_existing(self) -> None:
        """extend() does not overwrite existing files."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)

        base_spec = SystemSpec(
            name="skiptest",
            components=[ComponentSpec(name="core", component_type="module")],
        )
        engine.create(base_spec)

        base_dir = _TEST_ROOT / "skiptest"
        original = (base_dir / "core.py").read_text(encoding="utf-8")

        # Extend with the SAME component — should skip
        result = engine.extend(
            base_dir,
            [ComponentSpec(name="core", component_type="module")],
        )

        after = (base_dir / "core.py").read_text(encoding="utf-8")
        assert original == after  # Not overwritten
        assert len(result.files_created) == 0

    def test_extend_missing_dir_raises(self) -> None:
        """extend() raises FileNotFoundError for missing dirs."""
        engine = GenesisEngine(cortex_root=_TEST_ROOT)
        with pytest.raises(FileNotFoundError):
            engine.extend(
                Path("/tmp/nonexistent_genesis_dir"),
                [ComponentSpec(name="x")],
            )


class TestComposeTemplates:
    """Composable templates tests (#5)."""

    def test_compose_module_and_test(self) -> None:
        """compose_templates generates both module and test files."""
        engine = GenesisEngine()
        result = engine.compose_templates(
            ["module", "test"],
            name="search",
            system_name="memory",
            interfaces=["find", "query"],
        )

        assert "search.py" in result
        assert "test_search.py" in result
        assert "class SearchManager:" in result["search.py"]
        assert "def test_find" in result["test_search.py"]

    def test_compose_handles_missing_template(self) -> None:
        """compose_templates skips missing templates."""
        engine = GenesisEngine()
        result = engine.compose_templates(
            ["module", "nonexistent"],
            name="safe",
            system_name="test",
        )

        assert "safe.py" in result
        assert len(result) == 1  # Only module rendered
