"""Genesis Template Registry — deterministic ComponentSpec → Python source renderers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Optional

from cortex.extensions.genesis.models import ComponentSpec
from cortex.extensions.genesis.renderers import (
    _render_agent_yaml,
    _render_cli_command,
    _render_dataclass,
    _render_fastapi_route,
    _render_init,
    _render_migration,
    _render_mixin,
    _render_module,
    _render_protocol,
    _render_skill_md,
    _render_test,
    _render_workflow_md,
)

__all__ = ["TemplateRegistry", "SystemTemplate"]

logger = logging.getLogger("cortex.extensions.genesis.templates")

# Type alias: a renderer takes (spec_name, component) and returns file content
Renderer = Callable[[str, ComponentSpec], str]


class SystemTemplate:
    """A named template that knows how to render components into files.

    Attributes:
        name: Template identifier (e.g. "module", "skill").
        description: What this template generates.
        renderers: Mapping of filename pattern → renderer function.
    """

    def __init__(
        self,
        name: str,
        description: str,
        renderers: dict[str, Renderer],
    ) -> None:
        self.name = name
        self.description = description
        self.renderers = renderers

    def render(self, system_name: str, component: ComponentSpec) -> dict[str, str]:
        """Render a component into a dict of {relative_path: content}."""
        result: dict[str, str] = {}
        for filename_pattern, renderer in self.renderers.items():
            filename = filename_pattern.replace("{name}", component.name)
            filename = filename.replace("{system}", system_name)
            content = renderer(system_name, component)
            result[filename] = content
        return result


# ─────────────────────────────────────────────────────
# Renderer functions (imported from template_renderers)
# ─────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────
# Template Registry
# ─────────────────────────────────────────────────────


class TemplateRegistry:
    """Singleton registry of all available SystemTemplates."""

    def __init__(self) -> None:
        self._templates: dict[str, SystemTemplate] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the built-in templates."""
        self.register(
            SystemTemplate(
                name="module",
                description="Standard Python module with manager class",
                renderers={"{name}.py": _render_module},
            )
        )
        self.register(
            SystemTemplate(
                name="dataclass",
                description="Dataclass-based data model module",
                renderers={"{name}.py": _render_dataclass},
            )
        )
        self.register(
            SystemTemplate(
                name="mixin",
                description="CortexEngine mixin module",
                renderers={"{name}.py": _render_mixin},
            )
        )
        self.register(
            SystemTemplate(
                name="cli_command",
                description="Click CLI command group",
                renderers={"{name}_cmds.py": _render_cli_command},
            )
        )
        self.register(
            SystemTemplate(
                name="test",
                description="Pytest test file stub",
                renderers={"test_{name}.py": _render_test},
            )
        )
        self.register(
            SystemTemplate(
                name="init",
                description="Package __init__.py with exports",
                renderers={"__init__.py": _render_init},
            )
        )
        self.register(
            SystemTemplate(
                name="skill",
                description="Antigravity skill (SKILL.md)",
                renderers={"SKILL.md": _render_skill_md},
            )
        )
        self.register(
            SystemTemplate(
                name="workflow",
                description="Workflow markdown file",
                renderers={"{name}.md": _render_workflow_md},
            )
        )
        self.register(
            SystemTemplate(
                name="agent",
                description="YAML agent definition for AgentRegistry",
                renderers={"{name}.yaml": _render_agent_yaml},
            )
        )
        self.register(
            SystemTemplate(
                name="protocol",
                description="Python Protocol class (structural typing)",
                renderers={"{name}.py": _render_protocol},
            )
        )
        self.register(
            SystemTemplate(
                name="fastapi_route",
                description="FastAPI APIRouter module",
                renderers={"{name}_routes.py": _render_fastapi_route},
            )
        )
        self.register(
            SystemTemplate(
                name="migration",
                description="SQL migration script",
                renderers={"{name}.sql": _render_migration},
            )
        )

    def register(self, template: SystemTemplate) -> None:
        """Register a template by name."""
        self._templates[template.name] = template
        logger.debug("Registered template: %s", template.name)

    def get(self, name: str) -> Optional[SystemTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> list[dict[str, str]]:
        """List all registered templates."""
        return [{"name": t.name, "description": t.description} for t in self._templates.values()]

    @property
    def names(self) -> list[str]:
        """All registered template names."""
        return list(self._templates.keys())
