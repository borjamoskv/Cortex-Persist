"""Genesis Template Renderer Utils."""

from __future__ import annotations


def _ensure_self_param(interface: str) -> str:
    """Ensure an interface string has `self` as the first parameter."""
    if "(" not in interface:
        return f"{interface}(self) -> None"
    name_part, args_part = interface.split("(", 1)
    if args_part.lstrip().startswith("self"):
        return interface
    if args_part.startswith(")"):
        return f"{name_part}(self{args_part}"
    return f"{name_part}(self, {args_part}"
