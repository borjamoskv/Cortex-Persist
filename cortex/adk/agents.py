"""CORTEX ADK Agents — Sovereign AI Agent Definitions.

Defines multi-agent architecture using Google ADK:
- cortex_memory_agent: Root agent for memory operations
- cortex_analyst_agent: Cross-source analysis sub-agent
- cortex_guardian_agent: Ledger integrity and security sub-agent

Requires: pip install google-adk
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("cortex.adk.agents")

_ADK_INSTALL_MSG = "Google ADK not installed. Install with: pip install google-adk"

_ADK_AVAILABLE = False
try:
    from google.adk.agents.llm_agent import Agent

    _ADK_AVAILABLE = True
except ImportError:
    Agent = None  # type: ignore
    logger.debug(_ADK_INSTALL_MSG)


def is_adk_available() -> bool:
    """Check if Google ADK is installed."""
    return _ADK_AVAILABLE


# ─── Agent Definitions ────────────────────────────────────────────────

_DEFAULT_MODEL = os.environ.get("CORTEX_ADK_MODEL", "gemini-2.0-flash")


def create_memory_agent(
    model: str | None = None,
    extra_tools: list | None = None,
) -> Agent:
    """Create the CORTEX Memory Agent — root agent for sovereign memory ops.

    This agent can store facts, search memory, check system status,
    and verify ledger integrity. It's the primary entry point for
    all CORTEX memory operations.

    Args:
        model: LLM model to use (default: gemini-2.0-flash).
        extra_tools: Additional tools to register alongside CORTEX tools.

    Returns:
        Configured ADK Agent instance.

    Raises:
        ImportError: If google-adk is not installed.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)

    from cortex.adk.tools import ALL_TOOLS

    tools = list(ALL_TOOLS)
    if extra_tools:
        tools.extend(extra_tools)

    return Agent(
        model=model or _DEFAULT_MODEL,
        name="cortex_memory_agent",
        description=(
            "Sovereign memory agent for CORTEX. Stores, searches, and verifies "
            "facts across projects using hybrid semantic + text search and a "
            "cryptographically chained transaction ledger."
        ),
        instruction=(
            "You are the CORTEX Memory Agent — the sovereign guardian of "
            "persistent AI memory. Your responsibilities:\n\n"
            "1. **Store facts** — Use `adk_store` to persist decisions, errors, "
            "knowledge, ghosts, and bridges across projects.\n"
            "2. **Search memory** — Use `adk_search` for hybrid semantic + text "
            "retrieval. Always specify project when possible.\n"
            "3. **Monitor health** — Use `adk_status` to check system metrics.\n"
            "4. **Verify integrity** — Use `adk_ledger_verify` to audit the "
            "immutable transaction ledger.\n\n"
            "Rules:\n"
            "- Always confirm what was stored/found with the user.\n"
            "- Use fact_type accurately (knowledge, decision, error, ghost, etc).\n"
            "- Include relevant tags for discoverability.\n"
            "- Report ledger violations immediately.\n"
            "- Respond in the same language the user writes in."
        ),
        tools=tools,
    )


def create_analyst_agent(
    model: str | None = None,
    toolbox_tools: list | None = None,
) -> Agent:
    """Create the CORTEX Analyst Agent — cross-source analysis sub-agent.

    Combines CORTEX search with optional external database tools
    (via MCP Toolbox) for cross-source intelligence analysis.

    Args:
        model: LLM model to use.
        toolbox_tools: Additional Toolbox bridge tools for external DBs.

    Returns:
        Configured ADK Agent instance.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)

    from cortex.adk.tools import adk_search, adk_status

    tools: list = [adk_search, adk_status]
    if toolbox_tools:
        tools.extend(toolbox_tools)

    return Agent(
        model=model or _DEFAULT_MODEL,
        name="cortex_analyst_agent",
        description=(
            "Cross-source analyst that combines CORTEX memory search with "
            "external database queries for comprehensive intelligence analysis."
        ),
        instruction=(
            "You are the CORTEX Analyst — a cross-source intelligence engine.\n\n"
            "Your job is to find patterns across CORTEX memory AND external "
            "databases when available. When answering queries:\n"
            "1. Search CORTEX memory first for internal context.\n"
            "2. Query external databases if Toolbox tools are available.\n"
            "3. Synthesize findings into actionable intelligence.\n"
            "4. Always cite your sources (CORTEX fact IDs, external DB tables).\n"
            "5. Flag contradictions between internal memory and external data."
        ),
        tools=tools,
    )


def create_guardian_agent(
    model: str | None = None,
) -> Agent:
    """Create the CORTEX Guardian Agent — security and integrity sub-agent.

    Focused on ledger verification, integrity audits, and system
    health monitoring.

    Args:
        model: LLM model to use.

    Returns:
        Configured ADK Agent instance.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)

    from cortex.adk.tools import adk_ledger_verify, adk_status

    return Agent(
        model=model or _DEFAULT_MODEL,
        name="cortex_guardian_agent",
        description=(
            "Security and integrity guardian that monitors CORTEX ledger "
            "health, detects violations, and audits system state."
        ),
        instruction=(
            "You are the CORTEX Guardian — the sovereign security monitor.\n\n"
            "Your responsibilities:\n"
            "1. **Verify ledger integrity** — Run `adk_ledger_verify` to check "
            "the transaction chain for tampering.\n"
            "2. **Monitor system health** — Check `adk_status` for anomalies.\n"
            "3. **Report findings** — Always report violations with severity:\n"
            "   - 🔴 CRITICAL: Hash chain broken, data tampered\n"
            "   - 🟡 WARNING: Unusual patterns, high error rates\n"
            "   - 🟢 OK: System healthy, ledger intact\n"
            "4. **Recommend actions** — Suggest remediation for issues found."
        ),
        tools=[adk_ledger_verify, adk_status],
    )


# ─── Multi-Agent Orchestrator ─────────────────────────────────────────


def create_cortex_swarm(
    model: str | None = None,
    toolbox_tools: list | None = None,
) -> Agent:
    """Create the full CORTEX agent swarm — multi-agent system.

    Returns a root agent that can delegate to specialized sub-agents:
    - Memory Agent for store/search ops
    - Analyst Agent for cross-source analysis
    - Guardian Agent for security audits

    Args:
        model: LLM model for all agents.
        toolbox_tools: External DB tools for the analyst agent.

    Returns:
        Root Agent with sub-agent delegation.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)

    memory = create_memory_agent(model=model)
    analyst = create_analyst_agent(model=model, toolbox_tools=toolbox_tools)
    guardian = create_guardian_agent(model=model)

    return Agent(
        model=model or _DEFAULT_MODEL,
        name="cortex_sovereign",
        description=(
            "CORTEX Sovereign — the root orchestrator that coordinates memory, "
            "analysis, and security agents for comprehensive AI memory management."
        ),
        instruction=(
            "You are the CORTEX Sovereign — the root orchestrator of a "
            "multi-agent system for AI memory management.\n\n"
            "You coordinate three specialized agents:\n"
            "- **cortex_memory_agent**: For storing and searching facts\n"
            "- **cortex_analyst_agent**: For cross-source analysis\n"
            "- **cortex_guardian_agent**: For security and integrity audits\n\n"
            "Route requests to the appropriate agent based on the user's intent. "
            "For complex queries, coordinate multiple agents. "
            "Always report results clearly and respond in the user's language."
        ),
        sub_agents=[memory, analyst, guardian],
    )
