"""CORTEX CLI — Genesis command group.

Commands for the Genesis Engine — creating systems from specs.
Thin CLI wrapper; all logic lives in cortex.genesis.engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from cortex.cli.common import console


@click.group("genesis")
def genesis_group() -> None:
    """Genesis Engine — create systems from declarative specs."""
# pyright: reportCallIssue=false


@genesis_group.command("create")
@click.argument("name")
@click.option(
    "--type",
    "system_type",
    type=click.Choice(["module", "skill", "agent", "workflow"]),
    default="module",
    help="Type of system to create.",
)
@click.option(
    "--target",
    "target_dir",
    default=None,
    help="Target directory (defaults to cortex/<name>).",
)
@click.option("--cli/--no-cli", "auto_cli", default=False, help="Auto-generate CLI stubs.")
@click.option("--tests/--no-tests", "auto_tests", default=True, help="Auto-generate test stubs.")
@click.option("--description", "-d", default="", help="System description.")
def create(
    name: str,
    system_type: str,
    target_dir: str | None,
    auto_cli: bool,
    auto_tests: bool,
    description: str,
) -> None:
    """Create a new system from a minimal spec.

    NAME is the system identifier (snake_case).
    """
    from cortex.genesis import GenesisEngine, SystemSpec

    engine = GenesisEngine(
        cortex_root=Path(target_dir) if target_dir else None,
    )

    # Build a minimal spec with sensible defaults
    components = _default_components_for_type(system_type)

    spec = SystemSpec(
        name=name,
        description=description or f"Auto-generated {system_type}: {name}",
        system_type=system_type,
        auto_cli=auto_cli,
        auto_tests=auto_tests,
        components=components,
        tags=["genesis", system_type],
    )

    result = engine.create(spec)

    from rich.panel import Panel
    from rich.text import Text

    # Display results
    if result.validation_passed:
        status_color = "green"
        title = f"✅ Genesis complete: {name}"
    else:
        status_color = "red"
        title = f"❌ Genesis failed: {name}"

    content = Text()
    content.append(f"Files created: {len(result.files_created)}\n", style="cyan")
    if result.files_failed:
        content.append(f"Files failed:  {len(result.files_failed)}\n", style="bold red")
    content.append(f"CHRONOS-1:     {result.hours_saved:.2f}h saved\n", style="yellow")

    if result.validation_errors:
        content.append("\nValidation errors:\n", style="bold red")
        for err in result.validation_errors:
            content.append(f"   → {err}\n", style="red")

    if result.files_created:
        content.append("\nGenerated Paths:\n", style="bold")
        for f in result.files_created:
            content.append(f"   ↳ {f}\n", style="dim")

    console.print()
    panel = Panel(
        content,
        title=f"[bold {status_color}]{title}[/]",
        border_style=status_color,
        expand=False,
    )
    console.print(panel)


@genesis_group.command("from-yaml")
@click.argument("path", type=click.Path(exists=True))
def from_yaml(path: str) -> None:
    """Create a system from a YAML specification file."""
    import yaml

    from cortex.genesis import GenesisEngine

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]Failed to parse YAML:[/] {e}")
        sys.exit(1)

    engine = GenesisEngine()
    result = engine.create_from_dict(data)

    if result.validation_passed:
        console.print(f"\n[bold green]✅ Genesis from YAML:[/] {result.spec.name}")
    else:
        console.print(f"\n[bold red]❌ Genesis failed:[/] {result.spec.name}")

    console.print(f"   Files: {len(result.files_created)} | CHRONOS-1: {result.hours_saved:.2f}h")


@genesis_group.command("self")
def self_create() -> None:
    """Ω₀: Generate the Genesis Engine's own specification (auto-reference proof)."""
    from cortex.genesis import GenesisEngine

    engine = GenesisEngine()
    spec = engine.self_create()

    console.print("\n[bold cyan]∴ Genesis Self-Specification (Ω₀)[/]\n")
    console.print(f"  Name:       [green]{spec.name}[/]")
    console.print(f"  Type:       {spec.system_type}")
    console.print(f"  Components: {len(spec.components)}")
    console.print(f"  Auto-CLI:   {spec.auto_cli}")
    console.print(f"  Auto-Tests: {spec.auto_tests}")

    console.print("\n  [bold]Component Graph:[/]")
    for comp in spec.components:
        deps = f" → [{', '.join(comp.dependencies)}]" if comp.dependencies else ""
        console.print(f"    {comp.component_type:12s} [cyan]{comp.name}[/]{deps}")

    # Preview
    preview = engine.preview(spec)
    console.print("\n  [bold]File Preview:[/]")
    for comp_name, files in preview.items():
        for f in files:
            console.print(f"    [dim]{comp_name}/{f}[/]")

    # Output as JSON
    console.print("\n  [dim]JSON spec available via: cortex genesis self --json[/]")


@genesis_group.command("preview")
@click.argument("name")
@click.option("--type", "system_type", default="module")
def preview(name: str, system_type: str) -> None:
    """Preview what files would be created without writing anything."""
    from cortex.genesis import GenesisEngine, SystemSpec

    engine = GenesisEngine()
    components = _default_components_for_type(system_type)

    spec = SystemSpec(
        name=name,
        system_type=system_type,
        components=components,
    )

    file_map = engine.preview(spec)

    console.print(f"\n[bold]Genesis Preview:[/] {name} ({system_type})\n")
    for comp_name, files in file_map.items():
        for f in files:
            console.print(f"  [dim]{comp_name}/[/][cyan]{f}[/]")


@genesis_group.command("templates")
def list_templates() -> None:
    """List all available system templates."""
    from cortex.genesis import TemplateRegistry

    registry = TemplateRegistry()
    templates = registry.list_templates()

    console.print("\n[bold]Available Templates:[/]\n")
    for t in templates:
        console.print(f"  [cyan]{t['name']:15s}[/] {t['description']}")
    console.print()


@genesis_group.command("extend")
@click.argument("path", type=click.Path(exists=True))
@click.argument("components", nargs=-1, required=True)
@click.option(
    "--type",
    "component_type",
    default="module",
    help="Component type for all new components.",
)
@click.option("--tests/--no-tests", "auto_tests", default=False)
def extend(
    path: str,
    components: tuple[str, ...],
    component_type: str,
    auto_tests: bool,
) -> None:
    """Add components to an existing system.

    PATH is the existing system directory.
    COMPONENTS are the names of new components to add.
    """
    from cortex.genesis import ComponentSpec, GenesisEngine

    engine = GenesisEngine()
    new_comps = [ComponentSpec(name=name, component_type=component_type) for name in components]

    result = engine.extend(Path(path), new_comps, auto_tests=auto_tests)

    if result.files_created:
        console.print(
            f"\n[bold green]✅ Extended '{result.spec.name}':[/] "
            f"{len(result.files_created)} files added"
        )
        for f in result.files_created:
            console.print(f"   [dim]{f}[/]")
    else:
        console.print("\n[yellow]No new files added[/] — all components already exist.")

    console.print(f"   CHRONOS-1: [yellow]{result.hours_saved:.2f}h[/]")


@genesis_group.command("compose")
@click.argument("name")
@click.argument("templates_list", nargs=-1, required=True)
@click.option("--system", "system_name", default="cortex")
def compose(
    name: str,
    templates_list: tuple[str, ...],
    system_name: str,
) -> None:
    """Compose multiple templates for a single component.

    NAME is the component name.
    TEMPLATES are the template names to chain (e.g. module test mixin).
    """
    from cortex.genesis import GenesisEngine

    engine = GenesisEngine()
    result = engine.compose_templates(
        list(templates_list),
        name=name,
        system_name=system_name,
    )

    console.print(f"\n[bold]Composed {len(result)} files for '{name}':[/]\n")
    for filename, content in result.items():
        lines = content.count("\n") + 1
        console.print(f"  [cyan]{filename}[/] ({lines} lines)")
    console.print()


@genesis_group.command("specs")
def list_specs() -> None:
    """List available YAML specification templates."""
    specs_dir = Path(__file__).parent.parent / "genesis" / "specs"
    if not specs_dir.exists():
        console.print("[yellow]No specs directory found.[/]")
        return

    yaml_files = sorted(specs_dir.glob("*.yaml"))
    console.print("\n[bold]Available Genesis Specs:[/]\n")
    for f in yaml_files:
        console.print(f"  [cyan]{f.stem:20s}[/] cortex genesis from-yaml {f}")
    console.print()


def _default_components_for_type(system_type: str) -> list:
    """Generate sensible default components for a system type."""
    from cortex.genesis import ComponentSpec

    if system_type == "module":
        return [
            ComponentSpec(name="models", component_type="dataclass"),
            ComponentSpec(
                name="manager",
                component_type="module",
                dependencies=["models"],
            ),
        ]
    elif system_type == "skill":
        return [
            ComponentSpec(name="skill", component_type="skill"),
        ]
    elif system_type == "agent":
        return [
            ComponentSpec(name="agent", component_type="agent"),
        ]
    elif system_type == "workflow":
        return [
            ComponentSpec(name="workflow", component_type="workflow"),
        ]
    else:
        return [
            ComponentSpec(name="core", component_type="module"),
        ]
