"""CORTEX ADK Runner — CLI and Web interface for ADK agents.

Provides commands to run CORTEX agents interactively via CLI or
launch the ADK web dev UI.

Usage:
    python -m cortex.adk                        # Interactive CLI
    python -m cortex.adk --web                  # Web dev UI
    python -m cortex.adk --agent analyst        # Specific agent
    python -m cortex.adk --toolbox-url http://127.0.0.1:5000  # With Toolbox
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

__all__ = ["run_cli", "run_web", "main"]

logger = logging.getLogger("cortex.adk.runner")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CORTEX ADK Agent Runner",
        prog="cortex-adk",
    )
    parser.add_argument(
        "--agent",
        choices=["memory", "analyst", "guardian", "sovereign"],
        default="sovereign",
        help="Which agent to run (default: sovereign — full swarm)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model override (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the ADK web dev UI instead of CLI",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for web UI (default: 8000)",
    )
    parser.add_argument(
        "--toolbox-url",
        default=None,
        help="MCP Toolbox server URL (default: from TOOLBOX_URL env var)",
    )
    parser.add_argument(
        "--toolbox-toolset",
        default="",
        help="Named toolset to load from Toolbox (default: all tools)",
    )
    return parser.parse_args()


# ─── Toolbox Connection ──────────────────────────────────────────────


async def _connect_toolbox(
    server_url: str | None = None,
    toolset: str = "",
) -> list:
    """Attempt to connect to an MCP Toolbox server and return its tools.

    Returns an empty list if the Toolbox is not configured or unavailable.
    This is intentionally non-fatal — the agents work fine without it.
    """
    from cortex.mcp.toolbox_bridge import ToolboxBridge, ToolboxConfig

    config = ToolboxConfig.from_env()
    if server_url:
        config.server_url = server_url
        if server_url not in config.allowed_server_urls:
            config.allowed_server_urls.append(server_url)
    if toolset:
        config.toolset = toolset

    # Skip if no explicit URL and env default is empty/localhost without a running server
    if not server_url and config.server_url == "http://127.0.0.1:5000":
        # Only connect if TOOLBOX_URL was explicitly set
        import os

        if not os.environ.get("TOOLBOX_URL"):
            logger.debug("No TOOLBOX_URL configured — skipping Toolbox connection")
            return []

    bridge = ToolboxBridge(config)
    if not bridge.is_available:
        logger.info("Toolbox SDK not installed — running without external DB tools")
        return []

    connected = await bridge.connect()
    if connected:
        logger.info("Toolbox connected — loaded %d tools: %s", len(bridge.tools), bridge.tool_names)
        return bridge.tools

    logger.warning(
        "Could not connect to Toolbox at %s — running without external DB tools", config.server_url
    )
    return []


# ─── CLI Runner ──────────────────────────────────────────────────────


def run_cli(
    agent_name: str = "sovereign",
    model: str | None = None,
    toolbox_url: str | None = None,
    toolbox_toolset: str = "",
) -> None:
    """Run a CORTEX agent in interactive CLI mode."""
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        logger.error("Google ADK not installed. Install with: pip install google-adk")
        sys.exit(1)

    from cortex.adk.agents import (
        create_analyst_agent,
        create_cortex_swarm,
        create_guardian_agent,
        create_memory_agent,
    )

    # Connect to Toolbox if configured
    toolbox_tools = asyncio.run(_connect_toolbox(toolbox_url, toolbox_toolset))

    agent_map = {
        "memory": lambda: create_memory_agent(model=model),
        "analyst": lambda: create_analyst_agent(model=model, toolbox_tools=toolbox_tools or None),
        "guardian": lambda: create_guardian_agent(model=model),
        "sovereign": lambda: create_cortex_swarm(model=model, toolbox_tools=toolbox_tools or None),
    }

    agent = agent_map[agent_name]()
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="cortex", session_service=session_service)

    toolbox_status = f" + {len(toolbox_tools)} Toolbox tools" if toolbox_tools else ""
    print(f"\n🧠 CORTEX ADK — {agent.name}")
    print(f"   Model: {agent.model}{toolbox_status}")
    print("   Type 'quit' to exit\n")

    session = session_service.create_session(app_name="cortex", user_id="moskv-1")

    while True:
        try:
            user_input = input("cortex> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye.")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye.")
            break

        if not user_input:
            continue

        from google.genai import types

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)],
        )

        print()
        for event in runner.run(
            user_id="moskv-1",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
        print()


# ─── Web Runner ──────────────────────────────────────────────────────


def run_web(port: int = 8000) -> None:
    """Launch the ADK web dev UI."""
    try:
        from google.adk.cli import cli_tools_click

        sys.argv = ["adk", "web", "--port", str(port)]
        cli_tools_click.main()
    except ImportError:
        logger.error("Google ADK not installed. Install with: pip install google-adk")
        sys.exit(1)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the ADK runner."""
    args = _parse_args()

    if args.web:
        run_web(port=args.port)
    else:
        run_cli(
            agent_name=args.agent,
            model=args.model,
            toolbox_url=args.toolbox_url,
            toolbox_toolset=args.toolbox_toolset,
        )


if __name__ == "__main__":
    main()
