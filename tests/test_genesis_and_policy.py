"""Tests for cortex.genesis — GenesisEngine, SystemSpec, preview, CHRONOS-1.

No temp database required — Genesis operates on the filesystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── Models ──────────────────────────────────────────────────────────


class TestSystemSpec:
    def test_from_dict_minimal(self):
        from cortex.genesis.models import SystemSpec

        spec = SystemSpec.from_dict(
            {
                "name": "test_module",
                "components": [
                    {"name": "core", "component_type": "module"},
                ],
            }
        )
        assert spec.name == "test_module"
        assert len(spec.components) == 1
        assert spec.components[0].name == "core"

    def test_from_dict_full(self):
        from cortex.genesis.models import SystemSpec

        spec = SystemSpec.from_dict(
            {
                "name": "sovereign",
                "description": "Test system",
                "system_type": "agent",
                "auto_tests": True,
                "auto_cli": True,
                "tags": ["test", "agent"],
                "components": [
                    {
                        "name": "models",
                        "component_type": "dataclass",
                        "docstring": "Data models",
                        "interfaces": ["Fact", "Query"],
                        "dependencies": [],
                    },
                    {
                        "name": "engine",
                        "component_type": "module",
                        "dependencies": ["models"],
                    },
                ],
            }
        )
        assert spec.system_type == "agent"
        assert spec.auto_tests is True
        assert len(spec.components) == 2
        assert spec.components[1].dependencies == ["models"]

    def test_component_spec_defaults(self):
        from cortex.genesis.models import ComponentSpec

        comp = ComponentSpec(name="test")
        assert comp.component_type == "module"
        assert comp.interfaces == []
        assert comp.dependencies == []
        assert comp.template is None


# ─── Templates ───────────────────────────────────────────────────────


class TestTemplateRegistry:
    def test_registry_has_builtins(self):
        from cortex.genesis.templates import TemplateRegistry

        reg = TemplateRegistry()
        templates = reg.list_templates()
        names = [t["name"] if isinstance(t, dict) else t for t in templates]
        assert "module" in names
        assert len(names) >= 1

    def test_get_nonexistent_returns_none(self):
        from cortex.genesis.templates import TemplateRegistry

        reg = TemplateRegistry()
        assert reg.get("nonexistent_template_xyz") is None

    def test_module_template_renders(self):
        from cortex.genesis.models import ComponentSpec
        from cortex.genesis.templates import TemplateRegistry

        reg = TemplateRegistry()
        tmpl = reg.get("module")
        assert tmpl is not None

        comp = ComponentSpec(
            name="search",
            docstring="Semantic search module.",
        )
        rendered = tmpl.render("memory", comp)
        assert isinstance(rendered, dict)
        assert len(rendered) > 0
        # All rendered files should have string content
        for path, content in rendered.items():
            assert isinstance(path, str)
            assert isinstance(content, str)
            assert len(content) > 0


# ─── Validator ───────────────────────────────────────────────────────


class TestGenesisValidator:
    def test_validate_empty_created_list(self):
        from cortex.genesis.models import ComponentSpec, SystemSpec
        from cortex.genesis.validator import GenesisValidator

        v = GenesisValidator()
        spec = SystemSpec(
            name="empty",
            components=[
                ComponentSpec(name="core"),
            ],
        )
        passed, errors = v.validate(spec, [], Path("/tmp"))
        # Should still pass with warnings about missing files
        assert isinstance(passed, bool)
        assert isinstance(errors, list)


# ─── Engine ──────────────────────────────────────────────────────────


class TestGenesisEngine:
    def test_self_create_produces_valid_spec(self):
        """Ω₀: The engine can spec itself."""
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import SystemSpec

        engine = GenesisEngine()
        spec = engine.self_create()

        assert isinstance(spec, SystemSpec)
        assert spec.name == "genesis"
        assert len(spec.components) == 5
        assert spec.auto_tests is True
        assert spec.auto_cli is True

        # Verify component names
        names = {c.name for c in spec.components}
        assert "models" in names
        assert "engine" in names
        assert "templates" in names
        assert "assembler" in names
        assert "validator" in names

    def test_preview_returns_file_map(self):
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import ComponentSpec, SystemSpec

        engine = GenesisEngine()
        spec = SystemSpec(
            name="preview_test",
            components=[
                ComponentSpec(name="core", component_type="module"),
            ],
        )
        preview = engine.preview(spec)
        assert isinstance(preview, dict)
        assert "__auto__" in preview
        assert "__init__.py" in preview["__auto__"]

    def test_create_writes_files(self, tmp_path):
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import ComponentSpec, SystemSpec

        engine = GenesisEngine(cortex_root=tmp_path)
        spec = SystemSpec(
            name="test_system",
            components=[
                ComponentSpec(
                    name="core",
                    component_type="module",
                    docstring="Core module.",
                    interfaces=["init", "run"],
                ),
            ],
        )
        result = engine.create(spec)

        assert len(result.files_created) > 0
        assert result.hours_saved > 0
        # Verify files actually exist on disk
        for f in result.files_created:
            assert Path(f).exists(), f"File not found: {f}"

    def test_chronos_yield_positive(self):
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import ComponentSpec, SystemSpec

        engine = GenesisEngine()
        spec = SystemSpec(
            name="chronos_test",
            components=[
                ComponentSpec(
                    name="engine",
                    interfaces=["create", "delete", "update"],
                    dependencies=["models"],
                ),
                ComponentSpec(name="models", component_type="dataclass"),
            ],
        )
        hours = engine._calculate_chronos(spec, ["a.py", "b.py", "c.py"])
        assert hours > 0
        assert isinstance(hours, float)

    def test_estimate_complexity_range(self):
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import ComponentSpec, SystemSpec

        engine = GenesisEngine()
        spec = SystemSpec(
            name="simple",
            components=[ComponentSpec(name="x")],
        )
        c = engine._estimate_complexity(spec)
        assert 1 <= c <= 5

    def test_compose_templates(self):
        from cortex.genesis.engine import GenesisEngine

        engine = GenesisEngine()
        result = engine.compose_templates(
            ["module"],
            name="search",
            system_name="memory",
        )
        assert isinstance(result, dict)

    def test_extend_raises_on_missing_dir(self):
        from cortex.genesis.engine import GenesisEngine
        from cortex.genesis.models import ComponentSpec

        engine = GenesisEngine()
        with pytest.raises(FileNotFoundError):
            engine.extend(
                Path("/nonexistent/dir"),
                [ComponentSpec(name="x")],
            )


# ─── Model Policy Guard ─────────────────────────────────────────────


class TestModelPolicyGuard:
    def test_clean_presets_no_warnings(self, caplog):
        import logging

        from cortex.llm._presets import _validate_model_policy

        with caplog.at_level(logging.WARNING, logger="cortex.llm.presets"):
            _validate_model_policy(
                {
                    "good_provider": {
                        "default_model": "gpt-4o",
                        "intent_model_map": {
                            "code": "gemini-2.5-pro",
                        },
                    },
                }
            )
        assert "MODEL POLICY" not in caplog.text

    def test_prohibited_default_model_warns(self, caplog):
        import logging

        from cortex.llm._presets import _validate_model_policy

        with caplog.at_level(logging.WARNING, logger="cortex.llm.presets"):
            _validate_model_policy(
                {
                    "bad_provider": {
                        "default_model": "gpt-4o-mini",
                    },
                }
            )
        assert "MODEL POLICY" in caplog.text
        assert "gpt-4o-mini" in caplog.text

    def test_prohibited_intent_model_warns(self, caplog):
        import logging

        from cortex.llm._presets import _validate_model_policy

        with caplog.at_level(logging.WARNING, logger="cortex.llm.presets"):
            _validate_model_policy(
                {
                    "bad": {
                        "default_model": "claude-opus",
                        "intent_model_map": {
                            "code": "claude-haiku",
                        },
                    },
                }
            )
        assert "claude-haiku" in caplog.text

    def test_prohibited_tier_patterns(self):
        from cortex.llm._presets import _PROHIBITED_TIERS

        # Should match
        for model in [
            "gpt-4o-mini",
            "gemini-flash",
            "claude-haiku",
            "gemini-nano",
            "model-tiny",
            "something-small",
            "x-lite",
        ]:
            assert _PROHIBITED_TIERS.search(model), f"Should match: {model}"

        # Should NOT match
        for model in [
            "gpt-4o",
            "gemini-2.5-pro",
            "claude-sonnet-4",
            "gemini-2.5-pro",
            "deepseek-r1",
        ]:
            assert not _PROHIBITED_TIERS.search(model), f"Should NOT match: {model}"
