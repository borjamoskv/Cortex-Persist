# [C5-REAL] Exergy-Maximized
"""CORTEX Genesis - A System That Creates Systems.

Public API for the Genesis module. Import the engine,
specs, and templates from here.

Example::

    from babylon60.extensions.genesis import GenesisEngine, SystemSpec, ComponentSpec

    engine = GenesisEngine()
    spec = SystemSpec(name="my_module", components=[
        ComponentSpec(name="core", component_type="module"),
    ])
    result = engine.create(spec)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.extensions.genesis.assembler import SystemAssembler
    from babylon60.extensions.genesis.engine import GenesisEngine
    from babylon60.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec
    from babylon60.extensions.genesis.templates import SystemTemplate, TemplateRegistry
    from babylon60.extensions.genesis.validator import GenesisValidator

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
        from babylon60.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec

        _map = {
            "SystemSpec": SystemSpec,
            "ComponentSpec": ComponentSpec,
            "GenesisResult": GenesisResult,
        }
        return _map[name]

    if name == "GenesisEngine":
        from babylon60.extensions.genesis.engine import GenesisEngine

        return GenesisEngine

    if name in ("TemplateRegistry", "SystemTemplate"):
        from babylon60.extensions.genesis.templates import SystemTemplate, TemplateRegistry

        _map = {"TemplateRegistry": TemplateRegistry, "SystemTemplate": SystemTemplate}
        return _map[name]

    if name == "SystemAssembler":
        from babylon60.extensions.genesis.assembler import SystemAssembler

        return SystemAssembler

    if name == "GenesisValidator":
        from babylon60.extensions.genesis.validator import GenesisValidator

        return GenesisValidator

    msg = f"module 'cortex_extensions.genesis' has no attribute {name!r}"
    raise AttributeError(msg)
