"""CORTEX MCP — Genesis Engine Tools.

Exposes the Genesis Engine to AI agents via MCP,
enabling autonomous system creation from declarative specs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

__all__ = ["register_genesis_tools"]

logger = logging.getLogger("cortex.mcp.genesis_tools")


def register_genesis_tools(
    mcp: FastMCP,  # type: ignore[reportInvalidTypeForm]
    ctx: Any,
) -> None:
    """Register Genesis Engine tools on the MCP server.

    Tools registered:
      - cortex_genesis_create: Create a system from a spec dict
      - cortex_genesis_preview: Preview what files would be created
      - cortex_genesis_templates: List available templates
      - cortex_genesis_specs: List available YAML specs
    """

    @mcp.tool()
    async def cortex_genesis_create(
        name: str,
        system_type: str = "module",
        components: str = "[]",
        auto_tests: bool = True,
        auto_cli: bool = False,
        description: str = "",
    ) -> str:
        """Create a new system using the Genesis Engine.

        Args:
            name: System name (snake_case).
            system_type: module | skill | agent | workflow.
            components: JSON array of component specs, each with
                'name', 'component_type', optional 'interfaces',
                'dependencies', 'docstring'.
            auto_tests: Generate test stubs.
            auto_cli: Generate CLI command stubs.
            description: System description.

        Returns summary of created files and CHRONOS-1 yield.
        """
        from cortex.genesis import GenesisEngine, SystemSpec
        from cortex.genesis.models import ComponentSpec

        try:
            comp_list = json.loads(components) if components else []
        except (json.JSONDecodeError, TypeError):
            return "❌ Invalid JSON in 'components'"

        if not comp_list:
            comp_list = _default_comps_for_type(system_type)

        comps = [
            ComponentSpec(
                name=c.get("name", "core"),
                component_type=c.get("component_type", "module"),
                interfaces=c.get("interfaces", []),
                dependencies=c.get("dependencies", []),
                docstring=c.get("docstring", ""),
            )
            for c in comp_list
        ]

        spec = SystemSpec(  # type: ignore[type-error]
            name=name,
            description=description or f"Genesis: {name}",
            system_type=system_type,
            auto_tests=auto_tests,
            auto_cli=auto_cli,
            components=comps,
            tags=["genesis", system_type],
        )

        try:
            engine = GenesisEngine()  # type: ignore[type-error]
            result = engine.create(spec)
        except Exception as e:  # noqa: BLE001
            logger.error("Genesis create failed: %s", e)
            return f"❌ Genesis failed: {e}"

        status = "✅" if result.validation_passed else "⚠️"
        lines = [
            f"{status} Genesis: {name} ({system_type})",
            f"  Files created: {len(result.files_created)}",
            f"  CHRONOS-1: {result.hours_saved:.2f}h saved",
        ]
        if result.validation_errors:
            lines.append(f"  Warnings: {len(result.validation_errors)}")
        for f in result.files_created:
            lines.append(f"  → {f}")

        return "\n".join(lines)

    @mcp.tool()
    async def cortex_genesis_preview(
        name: str,
        system_type: str = "module",
    ) -> str:
        """Preview what files Genesis would create.

        Args:
            name: System name.
            system_type: module | skill | agent | workflow.
        """
        from cortex.genesis import GenesisEngine, SystemSpec
        from cortex.genesis.models import ComponentSpec

        comps = [ComponentSpec(**c) for c in _default_comps_for_type(system_type)]
        spec = SystemSpec(  # type: ignore[type-error]
            name=name,
            system_type=system_type,
            components=comps,
        )

        engine = GenesisEngine()  # type: ignore[type-error]
        preview = engine.preview(spec)

        lines = [f"Genesis Preview: {name} ({system_type})\n"]
        for comp_name, files in preview.items():
            for f in files:
                lines.append(f"  {comp_name}/{f}")
        return "\n".join(lines)

    @mcp.tool()
    async def cortex_genesis_templates() -> str:
        """List all available Genesis templates."""
        from cortex.genesis import TemplateRegistry

        registry = TemplateRegistry()  # type: ignore[type-error]
        templates = registry.list_templates()

        lines = ["Genesis Templates:\n"]
        for t in templates:
            lines.append(f"  {t['name']:15s} {t['description']}")
        return "\n".join(lines)

    @mcp.tool()
    async def cortex_genesis_specs() -> str:
        """List available YAML specification templates."""
        specs_dir = Path(__file__).parent.parent / "genesis" / "specs"
        if not specs_dir.exists():
            return "No specs directory found."

        yamls = sorted(specs_dir.glob("*.yaml"))
        lines = ["Genesis YAML Specs:\n"]
        for f in yamls:
            lines.append(f"  {f.stem}: {f}")
        return "\n".join(lines)


def _default_comps_for_type(
    system_type: str,
) -> list[dict[str, Any]]:
    """Default component specs for a system type."""
    if system_type == "module":
        return [
            {
                "name": "models",
                "component_type": "dataclass",
            },
            {
                "name": "manager",
                "component_type": "module",
                "dependencies": ["models"],
            },
        ]
    if system_type == "skill":
        return [{"name": "skill", "component_type": "skill"}]
    if system_type == "agent":
        return [{"name": "agent", "component_type": "agent"}]
    if system_type == "workflow":
        return [{"name": "workflow", "component_type": "workflow"}]
    return [{"name": "core", "component_type": "module"}]
