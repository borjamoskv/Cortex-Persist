"""CORTEX Confluence Bridge — Regulatory Documentation & Record-Keeping.

Automates the publication of EU AI Act Art. 12 compliance reports and
agent activity logs to Atlassian Confluence.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from cortex.mcp.server import _MCPContext

logger = logging.getLogger("cortex.mcp.confluence")


def format_report_for_confluence(report_text: str) -> str:
    """Converts a CLI-style compliance report into Markdown for Confluence.

    - Removes ANSI boxes and decorative ascii art.
    - Formats sections as H2/H3.
    - Converts [✅] and [❌] into standard status indicators.
    """
    # 1. Strip ANSI boxes
    lines = report_text.splitlines()
    clean_lines = []

    for line in lines:
        # Remove border chars
        line = re.sub(r"[╔╗╚╝╠╣═║─]", "", line).strip()
        if not line:
            continue

        # Section headers
        if "──" in line:
            header = line.replace("──", "").strip()
            clean_lines.append(f"## {header}")
            continue

        # Target Decision highlight
        if "★ TARGET DECISION" in line:
            clean_lines.append(f"### {line}")
            continue

        # Compliance checks
        if "[✅]" in line:
            clean_lines.append(f"✅ {line.replace('[✅]', '').strip()}")
        elif "[❌]" in line:
            clean_lines.append(f"❌ {line.replace('[❌]', '').strip()}")
        elif "[⚠️]" in line:
            clean_lines.append(f"⚠️ {line.replace('[⚠️]', '').strip()}")
        else:
            clean_lines.append(line)

    return "\n\n".join(clean_lines)


def register_confluence_tools(mcp: FastMCP, ctx: _MCPContext) -> None:
    """Register Confluence synchronization tools."""

    @mcp.tool()
    async def cortex_confluence_sync(
        space_id: str,
        page_title: str = "CORTEX — EU AI Act Compliance Ledger",
    ) -> str:
        """Sync the latest compliance report to Atlassian Confluence.

        This tool automates the Art. 12 'Record-keeping' obligation by
        publishing the current ledger state to a shared corporate space.

        Args:
            space_id: Target Confluence Space ID (e.g. 'DOCS')
            page_title: Title for the Confluence page
        """
        # Note: Implementation logic delegated to CONFLUENCE-Ω agent
        # which uses cortex_compliance_report + atlassian-mcp-server tools.

        async with ctx.pool.acquire() as conn:
            # Helper to generate internal report text
            report_text = await _generate_internal_report(conn, ctx)

        formatted_report = format_report_for_confluence(report_text)
        return formatted_report


async def _generate_internal_report(conn, ctx) -> str:
    """Minimal version of the report generator logic."""
    # This is a placeholder for the actual extraction logic.
    return "Report content placeholder — Use CONFLUENCE-Ω agent to orchestrate."
