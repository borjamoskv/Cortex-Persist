"""
CORTEX v6.1 — OpenAPI Spec Generator.

Exports the FastAPI OpenAPI schema as a static JSON file.
Useful for SDK generation, documentation portals, and API contracts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["export_openapi_spec", "get_openapi_spec"]

logger = logging.getLogger("cortex.openapi")


def get_openapi_spec() -> dict:
    """Return the OpenAPI spec dict from the FastAPI app."""
    from cortex.api.core import app

    return app.openapi()


def export_openapi_spec(
    output_path: str | Path | None = None,
    *,
    indent: int = 2,
) -> Path:
    """Export OpenAPI spec to a JSON file.

    Args:
        output_path: Destination file. Defaults to ``docs/openapi.json``.
        indent: JSON indentation level.

    Returns:
        Path to the written spec file.
    """
    spec = get_openapi_spec()

    if output_path is None:
        output_path = Path("docs") / "openapi.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(spec, indent=indent, ensure_ascii=False),
        encoding="utf-8",
    )

    endpoint_count = sum(len(methods) for methods in spec.get("paths", {}).values())
    logger.info(
        "OpenAPI spec exported: %s (%d endpoints, %d schemas)",
        output_path,
        endpoint_count,
        len(spec.get("components", {}).get("schemas", {})),
    )
    return output_path
