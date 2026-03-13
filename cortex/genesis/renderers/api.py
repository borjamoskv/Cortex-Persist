"""Genesis Template Renderers for REST API Routes."""

from __future__ import annotations

from cortex.genesis.models import ComponentSpec


def _render_fastapi_route(system_name: str, comp: ComponentSpec) -> str:
    """Render a FastAPI APIRouter module."""
    parts: list[str] = []
    docstring = comp.docstring or f"FastAPI routes for {system_name}.{comp.name}."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    parts.extend([
        "from fastapi import APIRouter, HTTPException",
        "",
        f'router = APIRouter(prefix="/{system_name}", tags=["{system_name}"])',
        "\n"
    ])

    if comp.interfaces:
        for iface in comp.interfaces:
            endpoint = iface.split("(")[0].strip()
            parts.extend([
                f'@router.get("/{endpoint}")',
                f"async def {endpoint}() -> dict[str, str]:",
                f'    """TODO: Implement {endpoint}."""',
                f'    return {{"status": "{endpoint} ok"}}',
                "\n"
            ])
    else:
        parts.extend([
            '@router.get("/status")',
            "async def status() -> dict[str, str]:",
            f'    """Health check for {system_name}."""',
            f'    return {{"service": "{system_name}", "status": "ok"}}',
            ""
        ])

    return "\n".join(parts)
