# [C5-REAL] Exergy-Maximized
"""CORTEX Genesis - A System That Creates Systems.

Public API for the Genesis module. Import the engine,
specs, and templates from here.

Example::

    from cortex.extensions.genesis import GenesisEngine, SystemSpec, ComponentSpec

    engine = GenesisEngine()
    spec = SystemSpec(name="my_module", components=[
        ComponentSpec(name="core", component_type="module"),
    ])
    result = engine.create(spec)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec
    from cortex.extensions.genesis.engine import GenesisEngine
    from cortex.extensions.genesis.templates import SystemTemplate, TemplateRegistry
    from cortex.extensions.genesis.assembler import SystemAssembler
    from cortex.extensions.genesis.validator import GenesisValidator

__all__ = [
    "ComponentSpec",  # pyright: ignore[reportUnsupportedDunderAll]
    "GenesisEngine",  # pyright: ignore[reportUnsupportedDunderAll]
    "GenesisResult",  # pyright: ignore[reportUnsupportedDunderAll]
    "GenesisValidator",  # pyright: ignore[reportUnsupportedDunderAll]
    "SystemAssembler",  # pyright: ignore[reportUnsupportedDunderAll]
    "SystemSpec",  # pyright: ignore[reportUnsupportedDunderAll]
    "SystemTemplate",  # pyright: ignore[reportUnsupportedDunderAll]
    "TemplateRegistry",  # pyright: ignore[reportUnsupportedDunderAll]
]


def __getattr__(name: str) -> object:
    """Lazy imports for all public symbols."""
    if name in ("SystemSpec", "ComponentSpec", "GenesisResult"):
        from cortex.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec

        _map = {
            "SystemSpec": SystemSpec,
            "ComponentSpec": ComponentSpec,
            "GenesisResult": GenesisResult,
        }
        return _map[name]

    if name == "GenesisEngine":
        from cortex.extensions.genesis.engine import GenesisEngine

        return GenesisEngine

    if name in ("TemplateRegistry", "SystemTemplate"):
        from cortex.extensions.genesis.templates import SystemTemplate, TemplateRegistry

        _map = {"TemplateRegistry": TemplateRegistry, "SystemTemplate": SystemTemplate}
        return _map[name]

    if name == "SystemAssembler":
        from cortex.extensions.genesis.assembler import SystemAssembler

        return SystemAssembler

    if name == "GenesisValidator":
        from cortex.extensions.genesis.validator import GenesisValidator

        return GenesisValidator

    msg = f"module 'cortex_extensions.genesis' has no attribute {name!r}"
    raise AttributeError(msg)
