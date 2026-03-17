"""Genesis Template Renderers for Python Code."""

from __future__ import annotations

from cortex.extensions.genesis.models import ComponentSpec
from cortex.extensions.genesis.renderers.utils import _ensure_self_param


def _render_module(system_name: str, comp: ComponentSpec) -> str:
    """Render a standard Python module file."""
    parts: list[str] = []
    docstring = comp.docstring or f"CORTEX Genesis — {system_name}.{comp.name} module."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    if comp.imports:
        parts.extend(sorted(comp.imports))
        parts.append("")

    class_name = "".join(word.capitalize() for word in comp.name.split("_"))
    if not class_name.endswith("Manager"):
        class_name += "Manager"

    parts.extend(["", f"class {class_name}:", f'    """Manager for {comp.name} operations."""', ""])

    if comp.interfaces:
        for interface in comp.interfaces:
            sig = _ensure_self_param(interface)
            method_name = interface.split("(")[0].strip()
            parts.extend(
                [
                    f"    def {sig}:",
                    f'        """TODO: Implement {method_name}."""',
                    "        raise NotImplementedError",
                    "",
                ]
            )
    else:
        parts.extend(["    pass", ""])

    return "\n".join(parts)


def _render_dataclass(system_name: str, comp: ComponentSpec) -> str:
    """Render a dataclass module."""
    parts: list[str] = []
    docstring = comp.docstring or f"CORTEX Genesis — {system_name}.{comp.name} data models."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    parts.extend(["from dataclasses import dataclass, field", "from typing import Any", ""])
    if comp.imports:
        parts.extend(sorted(comp.imports))
        parts.append("")

    class_name = "".join(word.capitalize() for word in comp.name.split("_"))
    parts.extend(
        [
            "",
            "@dataclass",
            f"class {class_name}:",
            f'    """{comp.docstring or f"Data model for {comp.name}."}"""',
            "",
            '    id: str = ""',
            '    name: str = ""',
            "    meta: dict[str, Any] = field(default_factory=dict)",
            "",
        ]
    )
    return "\n".join(parts)


def _render_mixin(system_name: str, comp: ComponentSpec) -> str:
    """Render a CortexEngine mixin."""
    parts: list[str] = []
    docstring = comp.docstring or f"CORTEX Genesis — {system_name}.{comp.name} mixin."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    parts.extend(["import logging", "from typing import Any", ""])
    if comp.imports:
        parts.extend(sorted(comp.imports))
        parts.append("")

    class_name = "".join(word.capitalize() for word in comp.name.split("_"))
    if not class_name.endswith("Mixin"):
        class_name += "Mixin"

    parts.extend(
        [
            f'logger = logging.getLogger("cortex.{system_name}.{comp.name}")\n\n',
            f"class {class_name}:",
            f'    """{comp.name} mixin for CortexEngine."""',
            "",
        ]
    )

    if comp.interfaces:
        for interface in comp.interfaces:
            method_name = interface.split("(")[0].strip()
            parts.extend(
                [
                    f"    async def {method_name}(self, **kwargs: Any) -> Any:",
                    f'        """TODO: Implement {method_name}."""',
                    "        raise NotImplementedError",
                    "",
                ]
            )
    else:
        parts.extend(["    pass", ""])

    return "\n".join(parts)


def _render_test(system_name: str, comp: ComponentSpec) -> str:
    """Render a pytest test file stub."""
    parts: list[str] = []
    parts.append(
        f'"""Tests for {system_name}.{comp.name}."""\n\nfrom __future__ import annotations\n'
    )
    if comp.imports:
        parts.extend(sorted(comp.imports))
        parts.append("")

    parts.append("")
    if comp.interfaces:
        for interface in comp.interfaces:
            method_name = interface.split("(")[0].strip()
            parts.extend(
                [
                    f"def test_{method_name}() -> None:",
                    f'    """Test {method_name}."""',
                    f"    # TODO: implement test for {method_name}",
                    "    assert True",
                    "",
                ]
            )
    else:
        parts.extend(
            [
                f"def test_{comp.name}_exists() -> None:",
                f'    """Smoke test for {comp.name}."""',
                "    assert True",
                "",
            ]
        )

    return "\n".join(parts)


def _render_init(system_name: str, comp: ComponentSpec) -> str:
    """Render an __init__.py with exports."""
    parts: list[str] = []
    docstring = comp.docstring or f"CORTEX Genesis — {system_name} package."
    parts.append(f'"""{docstring}"""\n')
    if comp.interfaces:
        exports = [f'    "{name.strip()}",' for name in comp.interfaces]
        parts.append("__all__ = [")
        parts.extend(exports)
        parts.append("]")
    else:
        parts.append("__all__: list[str] = []")
    parts.append("")
    return "\n".join(parts)


def _render_protocol(system_name: str, comp: ComponentSpec) -> str:
    """Render a Python Protocol class (structural typing)."""
    parts: list[str] = []
    docstring = comp.docstring or f"Protocol for {system_name}.{comp.name}."
    parts.append(f'"""{docstring}"""\n\nfrom __future__ import annotations\n')
    parts.extend(["from typing import Any, Protocol, runtime_checkable", ""])
    class_name = "".join(w.capitalize() for w in comp.name.split("_"))
    if not class_name.endswith("Protocol"):
        class_name += "Protocol"

    parts.extend(
        ["", "@runtime_checkable", f"class {class_name}(Protocol):", f'    """{docstring}"""', ""]
    )

    if comp.interfaces:
        for iface in comp.interfaces:
            method = iface.split("(")[0].strip()
            parts.extend([f"    def {method}(self, **kwargs: Any) -> Any:", "        ...", ""])
    else:
        parts.extend(["    def execute(self, **kwargs: Any) -> Any:", "        ...", ""])

    return "\n".join(parts)
