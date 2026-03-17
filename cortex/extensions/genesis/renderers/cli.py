"""Genesis Template Renderers for CLI Commands."""

from __future__ import annotations

from cortex.extensions.genesis.models import ComponentSpec


def _render_cli_command(system_name: str, comp: ComponentSpec) -> str:
    """Render a Click CLI command group."""
    parts: list[str] = []
    docstring = comp.docstring or f"CORTEX Genesis — CLI commands for {system_name}."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    parts.extend(["import click", ""])
    if comp.imports:
        parts.extend(sorted(comp.imports))
        parts.append("")

    group_name = system_name.replace("_", "-")
    parts.extend(
        [
            "",
            f'@click.group("{group_name}")',
            f"def {system_name}_group() -> None:",
            f'    """{docstring}"""\n\n',
        ]
    )

    if comp.interfaces:
        for interface in comp.interfaces:
            cmd_name = interface.split("(")[0].strip().replace("_", "-")
            func_name = interface.split("(")[0].strip()
            parts.extend(
                [
                    f'@{system_name}_group.command("{cmd_name}")',
                    f"def {func_name}() -> None:",
                    f'    """TODO: Implement {func_name}."""',
                    f'    click.echo("{func_name}: not yet implemented")',
                    "",
                ]
            )
    else:
        parts.extend(
            [
                f'@{system_name}_group.command("status")',
                "def status() -> None:",
                f'    """Show {system_name} status."""',
                f'    click.echo("{system_name}: operational")',
                "",
            ]
        )

    return "\n".join(parts)
