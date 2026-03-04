"""Tests for CORTEX MCP Mega Poderosas tools (production implementations)."""

import os
import tempfile

import pytest

from cortex.database.schema import CREATE_FACTS, CREATE_FACTS_INDEXES, CREATE_TRANSACTIONS
from cortex.mcp.server import create_mcp_server
from cortex.mcp.utils import MCPServerConfig


@pytest.fixture
def mcp_server(tmp_path):
    """Create MCP server with schema-initialized SQLite DB."""
    db_path = str(tmp_path / "test.db")

    # Initialize schema so tools can query real tables
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.executescript(CREATE_FACTS)
    conn.executescript(CREATE_FACTS_INDEXES)
    conn.executescript(CREATE_TRANSACTIONS)
    conn.commit()
    conn.close()

    cfg = MCPServerConfig(db_path=db_path)
    server = create_mcp_server(cfg)
    return server


@pytest.mark.asyncio
async def test_mega_tools_registration(mcp_server):
    """Verify that Mega Poderosas tools are registered in the MCP server."""
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    assert "cortex_reality_weaver" in tool_names
    assert "cortex_entropy_cracker" in tool_names
    assert "cortex_temporal_nexus" in tool_names


@pytest.mark.asyncio
async def test_reality_weaver_empty_project(mcp_server):
    """Reality Weaver should handle empty projects gracefully."""
    result = await mcp_server.call_tool(
        "cortex_reality_weaver", {"intent": "test auth", "project": "nonexistent_proj"}
    )
    text = "".join(str(getattr(c, "text", c)) for c in result)

    assert "REALITY WEAVING" in text.upper()
    assert "nonexistent_proj" in text
    assert "No facts found" in text
    assert "Orchestration Layer" in text


@pytest.mark.asyncio
async def test_reality_weaver_with_data(mcp_server, tmp_path):
    """Reality Weaver should report facts when DB has data."""
    import sqlite3

    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO facts (project, content, fact_type, valid_from, is_tombstoned) "
        "VALUES (?, ?, ?, datetime('now'), 0)",
        ("myproj", "Chose PostgreSQL over MySQL", "decision"),
    )
    conn.execute(
        "INSERT INTO facts (project, content, fact_type, valid_from, is_tombstoned) "
        "VALUES (?, ?, ?, datetime('now'), 0)",
        ("myproj", "TODO: add retry logic", "ghost"),
    )
    conn.commit()
    conn.close()

    result = await mcp_server.call_tool(
        "cortex_reality_weaver", {"intent": "expand API", "project": "myproj"}
    )
    text = "".join(str(getattr(c, "text", c)) for c in result)

    assert "REALITY WEAVING" in text.upper()
    assert "Knowledge Base" in text
    assert "decision" in text.lower()


@pytest.mark.asyncio
async def test_entropy_cracker_real_scan(mcp_server):
    """Entropy Cracker should scan real Python files and return metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "example.py")
        with open(test_file, "w") as f:
            f.write("class Foo:\n    def bar(self):\n        return 42\n\ndef baz():\n    pass\n")

        result = await mcp_server.call_tool("cortex_entropy_cracker", {"path": tmpdir})
        text = "".join(str(getattr(c, "text", c)) for c in result)

        assert "ENTROPY CRACKER" in text.upper()
        assert "Files Scanned:" in text
        assert "Density Score:" in text
        assert "Mean Entropy:" in text


@pytest.mark.asyncio
async def test_entropy_cracker_invalid_path(mcp_server):
    """Entropy Cracker should reject invalid paths gracefully."""
    result = await mcp_server.call_tool(
        "cortex_entropy_cracker", {"path": "/tmp/nonexistent_dir_xyz_123"}
    )
    text = "".join(str(getattr(c, "text", c)) for c in result)
    assert "not a valid directory" in text


@pytest.mark.asyncio
async def test_entropy_cracker_empty_dir(mcp_server):
    """Entropy Cracker should handle dirs with no Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await mcp_server.call_tool("cortex_entropy_cracker", {"path": tmpdir})
        text = "".join(str(getattr(c, "text", c)) for c in result)
        assert "No Python files" in text


@pytest.mark.asyncio
async def test_temporal_nexus_output(mcp_server):
    """Temporal Nexus should return real metrics from DB."""
    result = await mcp_server.call_tool("cortex_temporal_nexus", {"project": ""})
    text = "".join(str(getattr(c, "text", c)) for c in result)

    assert "TEMPORAL NEXUS" in text
    assert "Active Facts:" in text
    assert "Ghost Density:" in text
    assert "Temporal Drift" in text


@pytest.mark.asyncio
async def test_temporal_nexus_with_project(mcp_server):
    """Temporal Nexus should filter by project."""
    result = await mcp_server.call_tool("cortex_temporal_nexus", {"project": "cortex"})
    text = "".join(str(getattr(c, "text", c)) for c in result)

    assert "TEMPORAL NEXUS: cortex" in text
    assert "Drift:" in text
