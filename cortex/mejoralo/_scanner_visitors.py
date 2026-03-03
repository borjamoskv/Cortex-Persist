"""_scanner_visitors — AST visitors for BroadException and AsyncIntegrity scanners.

Extracted from antipatterns.py to satisfy the Landauer LOC barrier (≤500).
Visitors accept AntipatternFinding instances but do NOT import antipatterns.py
to avoid a circular dependency.
"""

from __future__ import annotations

import ast

from cortex.mejoralo.models import AntipatternFinding

__all__ = ["_BroadExceptionVisitor", "_AsyncIntegrityVisitor"]

# Mirrors the constant in antipatterns.py — kept in sync manually.
_BLOCKING_CALLS: dict[str, str] = {
    "time.sleep": "Use asyncio.sleep() instead",
    "requests.get": "Use httpx.AsyncClient or aiohttp",
    "requests.post": "Use httpx.AsyncClient or aiohttp",
    "requests.put": "Use httpx.AsyncClient or aiohttp",
    "requests.delete": "Use httpx.AsyncClient or aiohttp",
    "requests.request": "Use httpx.AsyncClient or aiohttp",
    "urllib.request.urlopen": "Use httpx.AsyncClient",
}


class _BroadExceptionVisitor(ast.NodeVisitor):
    """Detect `except Exception`, `except BaseException`, and bare `except:`."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            # Bare `except:`
            self.findings.append(
                AntipatternFinding(
                    scanner="BroadException",
                    severity="critical",
                    file=self.rel,
                    line=node.lineno,
                    message=(
                        "Bare `except:` catches all exceptions"
                        " including SystemExit/KeyboardInterrupt"
                    ),
                    fix_hint="Use a specific exception type: except ValueError, except OSError, etc.",
                )
            )
        elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
            body_is_silent = (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Pass | ast.Expr)
                and (
                    isinstance(node.body[0], ast.Pass)
                    or (
                        isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and node.body[0].value.value is ...
                    )
                )
            )
            severity = "critical" if body_is_silent else "high"
            msg = (
                f"`except {node.type.id}` with silent body — errors are being swallowed"
                if body_is_silent
                else f"`except {node.type.id}` is too broad"
                " — specific exceptions lose their identity"
            )
            self.findings.append(
                AntipatternFinding(
                    scanner="BroadException",
                    severity=severity,
                    file=self.rel,
                    line=node.lineno,
                    message=msg,
                    fix_hint="Catch specific exceptions: except (ValueError, KeyError, OSError) as e:",
                )
            )
        self.generic_visit(node)


class _AsyncIntegrityVisitor(ast.NodeVisitor):
    """Detect blocking I/O calls inside async functions."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings
        self._in_async = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        old = self._in_async
        self._in_async = True
        self.generic_visit(node)
        self._in_async = old

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old = self._in_async
        self._in_async = False
        self.generic_visit(node)
        self._in_async = old

    def visit_Call(self, node: ast.Call) -> None:
        if not self._in_async:
            self.generic_visit(node)
            return

        call_name = self._get_call_name(node)
        if call_name and call_name in _BLOCKING_CALLS:
            self.findings.append(
                AntipatternFinding(
                    scanner="AsyncIntegrity",
                    severity="high",
                    file=self.rel,
                    line=node.lineno,
                    message=f"Blocking call `{call_name}()` inside async function",
                    fix_hint=_BLOCKING_CALLS[call_name],
                )
            )
        self.generic_visit(node)

    @staticmethod
    def _get_call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            parts.reverse()
            return ".".join(parts)
        return None
