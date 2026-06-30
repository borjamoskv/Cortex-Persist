#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: sql-security-auditor
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P0
"""

import ast
import os
import sys
from pathlib import Path
from typing import Any

# Excepciones válidas que no requieren tenant_id (por ejemplo, tablas globales, metadata del sistema o índices)
TABLE_BYPASS_EXCEPTIONS = [
    "sqlite_master",
    "sqlite_schema",
    "pragma",
    "create table",
    "create index",
    "drop table",
    "alter table",
    "begin transaction",
    "commit",
    "rollback",
]


class SQLQueryVisitor(ast.NodeVisitor):
    """AST Visitor that scans python code for raw SQL execution calls and validates security parameters."""

    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.lines = content.splitlines()
        self.violations: list[dict[str, Any]] = []

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _is_bypass(self, start_line: int, end_line: int) -> bool:
        for l in range(start_line, end_line + 1):
            snippet = self._get_line_snippet(l)
            if "# nosec" in snippet or "# bypass-tenant" in snippet:
                return True
        return False

    def visit_Call(self, node: ast.Call):
        # Scan for calls like conn.execute(), cursor.execute(), self._conn.execute()
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany"):
            if not node.args:
                return

            lineno = node.lineno
            end_lineno = getattr(node, "end_lineno", lineno) or lineno
            if self._is_bypass(lineno, end_lineno):
                return

            query_node = node.args[0]
            self._analyze_query_node(query_node, lineno, node.func.attr)

        self.generic_visit(node)

    def _analyze_query_node(self, query_node: ast.expr, lineno: int, call_type: str):
        snippet = self._get_line_snippet(lineno)

        # 1. Check for SQL Injection risks (string formatting / concatenation)
        if isinstance(query_node, ast.JoinedStr):
            # JoinedStr is an f-string
            # Exception: f-strings that only interpolate placeholders, e.g., f"INSERT INTO x VALUES ({placeholders})"
            # We strictly flag f-strings unless they are marked with an override, to maintain C5-REAL zero-trust.
            self.violations.append({
                "type": "SQL_INJECTION_RISK",
                "severity": "CRITICAL",
                "message": f"F-string format used in SQL execute: {snippet}",
                "line": lineno,
                "snippet": snippet
            })
            return

        elif isinstance(query_node, ast.BinOp) and isinstance(query_node.op, (ast.Mod, ast.Add)):
            # % operator or string concatenation +
            self.violations.append({
                "type": "SQL_INJECTION_RISK",
                "severity": "CRITICAL",
                "message": f"String concatenation or modulo formatting used in SQL execute: {snippet}",
                "line": lineno,
                "snippet": snippet
            })
            return

        elif isinstance(query_node, ast.Call) and isinstance(query_node.func, ast.Attribute) and query_node.func.attr == "format":
            # format() method call
            self.violations.append({
                "type": "SQL_INJECTION_RISK",
                "severity": "CRITICAL",
                "message": f".format() method used in SQL execute: {snippet}",
                "line": lineno,
                "snippet": snippet
            })
            return

        # 2. Check for tenant_id presence in static string queries
        elif isinstance(query_node, ast.Constant) and isinstance(query_node.value, str):
            query_str = query_node.value.lower()
            self._validate_query_content(query_str, lineno, snippet)

    def _validate_query_content(self, query_str: str, lineno: int, snippet: str):
        # We only check typical queries that select or mutate fact/session tables
        sql_keywords = ["select", "insert", "update", "delete"]
        if not any(kw in query_str for kw in sql_keywords):
            return

        # If it matches any bypass exception, skip
        if any(exc in query_str for exc in TABLE_BYPASS_EXCEPTIONS):
            return

        # Core logic: All operational queries MUST contain 'tenant_id'
        if "tenant_id" not in query_str:
            self.violations.append({
                "type": "MISSING_TENANT_ISOLATION",
                "severity": "CRITICAL",
                "message": "SQL query lacks strict 'tenant_id' constraint filter.",
                "line": lineno,
                "snippet": snippet
            })


def audit_file(filepath: Path) -> list[dict[str, Any]]:
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
        visitor = SQLQueryVisitor(str(filepath), content)
        visitor.visit(tree)
        return visitor.violations
    except Exception as e:
        return [{
            "type": "PARSE_ERROR",
            "severity": "HIGH",
            "message": f"Failed to parse file AST: {e}",
            "line": 0,
            "snippet": ""
        }]


def main():
    target_dir = Path(__file__).resolve().parent.parent / "babylon60" / "memory"
    if not target_dir.exists():
        print(f"Error: Target directory {target_dir} not found.")
        sys.exit(1)

    print(f"Igniting SQL Security Audit over: {target_dir}")
    total_violations = 0
    files_scanned = 0

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = Path(root) / file
                files_scanned += 1
                violations = audit_file(filepath)
                if violations:
                    print(f"\n📁 Violations found in {filepath.relative_to(target_dir.parent.parent)}:")
                    for v in violations:
                        severity_color = "🔴" if v["severity"] == "CRITICAL" else "🟡"
                        print(f"  {severity_color} [Line {v['line']}] [{v['type']}] {v['message']}")
                        if v["snippet"]:
                            print(f"     Code: {v['snippet']}")
                        total_violations += 1

    print("\n" + "=" * 60)
    print(f"Audit complete. Scanned {files_scanned} files.")
    if total_violations > 0:
        print(f"❌ Found {total_violations} security violations. Zero-Trust C5-REAL boundary breached.")
        sys.exit(1)
    else:
        print("✅ Zero SQL violations detected. Strict Tenant Isolation and injection barriers intact.")
        sys.exit(0)


if __name__ == "__main__":
    main()
