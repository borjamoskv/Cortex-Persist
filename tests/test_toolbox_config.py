"""Tests for MCP Toolbox tools.yaml configuration.

Validates YAML structure, SQL syntax, and toolset references without
requiring the Toolbox binary. Creates an in-memory SQLite database with
the full CORTEX schema and prepares each tool's statement.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

# ─── Fixtures ─────────────────────────────────────────────────────────

TOOLS_YAML = Path(__file__).resolve().parent.parent / "cortex" / "mcp" / "toolbox" / "tools.yaml"

VALID_TOOL_PARAM_TYPES = {"string", "integer", "float", "boolean"}


@pytest.fixture(scope="module")
def docs() -> list[dict]:
    """Load and parse all YAML documents from tools.yaml."""
    assert TOOLS_YAML.exists(), f"tools.yaml not found at {TOOLS_YAML}"
    with TOOLS_YAML.open() as fh:
        return list(yaml.safe_load_all(fh))


@pytest.fixture(scope="module")
def tools(docs: list[dict]) -> list[dict]:
    """Extract tool documents."""
    return [d for d in docs if d and d.get("kind") == "tools"]


@pytest.fixture(scope="module")
def toolsets(docs: list[dict]) -> list[dict]:
    """Extract toolset documents."""
    return [d for d in docs if d and d.get("kind") == "toolsets"]


@pytest.fixture(scope="module")
def sources(docs: list[dict]) -> list[dict]:
    """Extract source documents."""
    return [d for d in docs if d and d.get("kind") == "sources"]


@pytest.fixture(scope="module")
def cortex_db() -> sqlite3.Connection:
    """Create in-memory SQLite DB with CORTEX schema for SQL validation."""
    from cortex.database.schema import ALL_SCHEMA

    conn = sqlite3.connect(":memory:")
    for stmt in ALL_SCHEMA:
        # Skip triggers and FTS that may use special syntax
        try:
            conn.executescript(stmt)
        except sqlite3.OperationalError:
            pass  # Virtual tables (vec0) won't work in vanilla SQLite
    return conn


# ─── Structure Tests ──────────────────────────────────────────────────


def test_yaml_loads(docs: list[dict]) -> None:
    """tools.yaml must parse without errors."""
    assert len(docs) > 0, "tools.yaml is empty"


def test_has_source(sources: list[dict]) -> None:
    """At least one source must be defined."""
    assert len(sources) >= 1
    assert sources[0]["name"] == "cortex-db"
    assert sources[0]["type"] == "sqlite"


def test_has_tools(tools: list[dict]) -> None:
    """Must have at least the 5 planned tools."""
    names = {t["name"] for t in tools}
    expected = {
        "query-facts",
        "query-ghosts",
        "query-decisions",
        "query-signals",
        "cortex-stats",
        "trace-impact",
        "cluster-signals",
        "ghost-mapping",
    }
    assert expected.issubset(names), f"Missing tools: {expected - names}"


def test_tool_required_fields(tools: list[dict]) -> None:
    """Every tool must have name, type, source, description, statement."""
    for tool in tools:
        for field in ("name", "type", "source", "description", "statement"):
            assert field in tool, f"Tool '{tool.get('name', '?')}' missing field '{field}'"


def test_tool_param_types(tools: list[dict]) -> None:
    """All parameter types must be valid."""
    for tool in tools:
        for param in tool.get("parameters", []):
            assert (
                param["type"] in VALID_TOOL_PARAM_TYPES
            ), f"Tool '{tool['name']}' param '{param['name']}' has invalid type '{param['type']}'"


def test_toolset_references(tools: list[dict], toolsets: list[dict]) -> None:
    """Every tool referenced in a toolset must exist as a defined tool."""
    tool_names = {t["name"] for t in tools}
    for ts in toolsets:
        for ref in ts.get("tools", []):
            assert ref in tool_names, f"Toolset '{ts['name']}' references non-existent tool '{ref}'"


def test_has_toolsets(toolsets: list[dict]) -> None:
    """Must have cortex-readonly, cortex-summary, and graph-analysis toolsets."""
    names = {ts["name"] for ts in toolsets}
    assert "cortex-readonly" in names
    assert "cortex-summary" in names
    assert "graph-analysis" in names


# ─── SQL Validation Tests ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "tool_name",
    [
        "query-facts",
        "query-ghosts",
        "query-decisions",
        "query-signals",
        "cortex-stats",
        "trace-impact",
        "cluster-signals",
        "ghost-mapping",
    ],
)
def test_sql_prepares(tool_name: str, tools: list[dict], cortex_db: sqlite3.Connection) -> None:
    """Each tool's SQL statement must prepare successfully against the schema.

    We replace $N placeholders with NULL for syntax validation only.
    """
    tool = next(t for t in tools if t["name"] == tool_name)
    stmt = tool["statement"]

    # Replace Toolbox-style ? placeholders with NULL for prepare check
    prepared = stmt.replace("?", "NULL")

    try:
        cortex_db.execute(prepared)
    except sqlite3.OperationalError as exc:
        pytest.fail(f"SQL validation failed for tool '{tool_name}': {exc}\n\nSQL:\n{prepared}")


def test_all_tools_read_only(tools: list[dict]) -> None:
    """No tool statement should contain write operations."""
    write_keywords = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}
    for tool in tools:
        stmt_upper = tool["statement"].upper()
        for kw in write_keywords:
            # Allow keywords inside comments or string literals — crude but effective
            # We check if the keyword appears as a standalone word
            import re

            if re.search(rf"\b{kw}\b", stmt_upper):
                pytest.fail(
                    f"Tool '{tool['name']}' contains write keyword '{kw}' — "
                    f"Toolbox tools must be read-only (Ω₃)"
                )
