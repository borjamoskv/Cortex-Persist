"""Registry for AST handlers and specialized scanners."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Scanner(Protocol):
    """Protocol for specialized guards scanners."""
    def scan(self, node: Any) -> list[tuple[int, str, str]]:
        ...
