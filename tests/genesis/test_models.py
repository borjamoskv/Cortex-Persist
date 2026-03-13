"""Tests for cortex.genesis.models — SystemSpec, ComponentSpec, GenesisResult."""

from __future__ import annotations

from cortex.genesis.models import ComponentSpec, GenesisResult, SystemSpec


class TestComponentSpec:
    """ComponentSpec dataclass tests."""

    def test_defaults(self) -> None:
        comp = ComponentSpec(name="core")
        assert comp.name == "core"
        assert comp.component_type == "module"
        assert comp.imports == []
        assert comp.interfaces == []
        assert comp.dependencies == []
        assert comp.template is None
        assert comp.docstring == ""

    def test_to_dict_roundtrip(self) -> None:
        comp = ComponentSpec(
            name="models",
            component_type="dataclass",
            imports=["from typing import Any"],
            interfaces=["to_dict", "from_dict"],
            dependencies=["core"],
            template="dataclass",
            docstring="Data models.",
        )
        d = comp.to_dict()
        restored = ComponentSpec.from_dict(d)
        assert restored.name == comp.name
        assert restored.component_type == comp.component_type
        assert restored.imports == comp.imports
        assert restored.interfaces == comp.interfaces
        assert restored.dependencies == comp.dependencies
        assert restored.template == comp.template
        assert restored.docstring == comp.docstring

    def test_from_dict_minimal(self) -> None:
        comp = ComponentSpec.from_dict({"name": "x"})
        assert comp.name == "x"
        assert comp.component_type == "module"


class TestSystemSpec:
    """SystemSpec dataclass tests."""

    def test_defaults(self) -> None:
        spec = SystemSpec(name="test_system")
        assert spec.name == "test_system"
        assert spec.description == ""
        assert spec.system_type == "module"
        assert spec.auto_cli is False
        assert spec.auto_tests is False
        assert spec.components == []
        assert spec.tags == []

    def test_to_dict_roundtrip(self) -> None:
        spec = SystemSpec(
            name="my_sys",
            description="A test system",
            target_dir="output",
            system_type="skill",
            auto_cli=True,
            auto_tests=True,
            tags=["test", "genesis"],
            components=[
                ComponentSpec(name="a"),
                ComponentSpec(name="b", dependencies=["a"]),
            ],
        )
        d = spec.to_dict()
        restored = SystemSpec.from_dict(d)
        assert restored.name == spec.name
        assert restored.description == spec.description
        assert restored.system_type == spec.system_type
        assert restored.auto_cli == spec.auto_cli
        assert len(restored.components) == 2
        assert restored.components[1].dependencies == ["a"]

    def test_from_dict_minimal(self) -> None:
        spec = SystemSpec.from_dict({"name": "x"})
        assert spec.name == "x"
        assert spec.system_type == "module"


class TestGenesisResult:
    """GenesisResult dataclass tests."""

    def test_summary_passed(self) -> None:
        result = GenesisResult(
            spec=SystemSpec(name="test"),
            files_created=["a.py", "b.py"],
            validation_passed=True,
            hours_saved=1.5,
        )
        s = result.summary()
        assert "✅ PASSED" in s
        assert "2 files" in s
        assert "1.50h" in s

    def test_summary_failed(self) -> None:
        result = GenesisResult(
            spec=SystemSpec(name="fail"),
            files_created=[],
            validation_passed=False,
            validation_errors=["missing __init__.py"],
            hours_saved=0.0,
        )
        s = result.summary()
        assert "❌ FAILED" in s

    def test_created_at_populated(self) -> None:
        result = GenesisResult(spec=SystemSpec(name="t"))
        assert result.created_at != ""
        # Should be a parseable timestamp
        assert "T" in result.created_at or len(result.created_at) > 10
