"""Tests for cortex.genesis.templates — TemplateRegistry and renderers."""

from __future__ import annotations

from cortex.extensions.genesis.models import ComponentSpec
from cortex.extensions.genesis.templates import TemplateRegistry


class TestTemplateRegistry:
    """TemplateRegistry singleton and registration tests."""

    def test_default_templates_registered(self) -> None:
        reg = TemplateRegistry()
        expected = {
            "module",
            "dataclass",
            "mixin",
            "cli_command",
            "test",
            "init",
            "skill",
            "workflow",
            "agent",
            "protocol",
            "fastapi_route",
            "migration",
        }
        assert set(reg.names) == expected

    def test_get_existing_template(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("module")
        assert tmpl is not None
        assert tmpl.name == "module"

    def test_get_missing_template(self) -> None:
        reg = TemplateRegistry()
        assert reg.get("nonexistent") is None

    def test_list_templates(self) -> None:
        reg = TemplateRegistry()
        listing = reg.list_templates()
        assert len(listing) == 12
        assert all("name" in t and "description" in t for t in listing)


class TestModuleRenderer:
    """Verify the module template produces valid Python."""

    def test_renders_class_with_interfaces(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("module")
        assert tmpl is not None

        comp = ComponentSpec(
            name="my_manager",
            component_type="module",
            interfaces=["process", "run"],
            docstring="Test module.",
        )
        result = tmpl.render("test_sys", comp)
        assert len(result) == 1

        content = list(result.values())[0]
        assert "class MyManagerManager:" in content or "class MyManager:" in content
        assert "def process" in content or "def run" in content

    def test_renders_empty_interfaces(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("module")
        assert tmpl is not None

        comp = ComponentSpec(name="empty", component_type="module")
        result = tmpl.render("test_sys", comp)
        content = list(result.values())[0]
        assert "pass" in content


class TestDataclassRenderer:
    """Verify the dataclass template produces valid Python."""

    def test_renders_dataclass(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("dataclass")
        assert tmpl is not None

        comp = ComponentSpec(name="event_data", component_type="dataclass")
        result = tmpl.render("events", comp)
        content = list(result.values())[0]
        assert "@dataclass" in content
        assert "class EventData:" in content
        assert "from dataclasses import dataclass" in content


class TestMixinRenderer:
    """Verify the mixin template produces valid Python."""

    def test_renders_mixin(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("mixin")
        assert tmpl is not None

        comp = ComponentSpec(
            name="search",
            component_type="mixin",
            interfaces=["hybrid_search"],
        )
        result = tmpl.render("memory", comp)
        content = list(result.values())[0]
        assert "class SearchMixin:" in content
        assert "async def hybrid_search" in content


class TestSkillRenderer:
    """Verify the skill template produces valid SKILL.md."""

    def test_renders_skill_md(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("skill")
        assert tmpl is not None

        comp = ComponentSpec(
            name="tactical_nav",
            component_type="skill",
            docstring="Tactical navigation engine.",
        )
        result = tmpl.render("tactical_nav", comp)
        content = list(result.values())[0]
        assert "name:" in content
        assert "Tactical navigation engine." in content


class TestAgentRenderer:
    """Verify the agent template produces valid YAML."""

    def test_renders_agent_yaml(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("agent")
        assert tmpl is not None

        comp = ComponentSpec(name="scout", component_type="agent")
        result = tmpl.render("scout", comp)
        content = list(result.values())[0]
        assert "name:" in content
        assert "model:" in content
        assert "system_prompt:" in content
        assert "memory:" in content


class TestCliRenderer:
    """Verify the CLI template produces valid Click code."""

    def test_renders_cli_group(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("cli_command")
        assert tmpl is not None

        comp = ComponentSpec(
            name="monitor",
            component_type="cli_command",
            interfaces=["start", "stop"],
        )
        result = tmpl.render("monitor", comp)
        content = list(result.values())[0]
        assert "@click.group" in content
        assert "def start" in content
        assert "def stop" in content


class TestProtocolRenderer:
    """Verify the protocol template produces valid Python Protocol."""

    def test_renders_protocol(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("protocol")
        assert tmpl is not None

        comp = ComponentSpec(
            name="storage",
            component_type="protocol",
            interfaces=["save", "load", "delete"],
            docstring="Storage protocol.",
        )
        result = tmpl.render("persistence", comp)
        content = list(result.values())[0]
        assert "@runtime_checkable" in content
        assert "class StorageProtocol(Protocol):" in content
        assert "def save" in content
        assert "def load" in content


class TestFastAPIRouteRenderer:
    """Verify the FastAPI route template."""

    def test_renders_routes(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("fastapi_route")
        assert tmpl is not None

        comp = ComponentSpec(
            name="health",
            component_type="fastapi_route",
            interfaces=["status", "metrics"],
        )
        result = tmpl.render("health", comp)
        assert "health_routes.py" in result
        content = result["health_routes.py"]
        assert "APIRouter" in content
        assert "@router.get" in content
        assert "async def status" in content
        assert "async def metrics" in content


class TestMigrationRenderer:
    """Verify the migration template produces valid SQL."""

    def test_renders_migration(self) -> None:
        reg = TemplateRegistry()
        tmpl = reg.get("migration")
        assert tmpl is not None

        comp = ComponentSpec(
            name="facts_v2",
            component_type="migration",
            docstring="Add v2 columns to facts table.",
        )
        result = tmpl.render("cortex", comp)
        content = list(result.values())[0]
        assert "CREATE TABLE" in content
        assert "facts_v2" in content
        assert "CREATE INDEX" in content
