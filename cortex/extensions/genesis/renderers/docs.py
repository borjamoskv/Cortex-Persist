"""Genesis Template Renderers for Markdown Documentation."""

from __future__ import annotations

import textwrap

from cortex.extensions.genesis.models import ComponentSpec


def _render_skill_md(system_name: str, comp: ComponentSpec) -> str:
    """Render a SKILL.md for an Antigravity skill."""
    title = system_name.replace("_", " ").title()
    description = comp.docstring or f"Auto-generated skill: {title}"
    return textwrap.dedent(f"""\
        ---
        name: {title}
        description: "{description}"
        version: 1.0.0
        created: auto-generated
        category: genesis
        ---

        # {title}

        > {description}

        ## Usage

        Invoke via `/genesis` or programmatically via `GenesisEngine`.

        ## Implementation

        TODO: Add implementation details.
    """)


def _render_workflow_md(system_name: str, comp: ComponentSpec) -> str:
    """Render a workflow markdown file."""
    title = system_name.replace("_", " ").title()
    description = comp.docstring or f"Auto-generated workflow: {title}"
    return textwrap.dedent(f"""\
        ---
        description: {description}
        ---

        # {title} Workflow

        ## Steps

        1. TODO: Define step 1
        2. TODO: Define step 2
        3. TODO: Define step 3
    """)
