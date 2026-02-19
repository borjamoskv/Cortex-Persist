"""CORTEX ADK Runner — CLI and Web interface for ADK agents.

Provides commands to run CORTEX agents interactively via CLI or
launch the ADK web dev UI.

Usage:
    python -m cortex.adk.runner            # Interactive CLI
    python -m cortex.adk.runner --web      # Web dev UI
    python -m cortex.adk.runner --agent analyst  # Specific agent
"""

from __future__ import annotations

import argparse
import logging
import sys

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
    return parser.parse_args()


def run_cli(agent_name: str = "sovereign", model: str | None = None) -> None:
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

    agent_map = {
        "memory": lambda: create_memory_agent(model=model),
        "analyst": lambda: create_analyst_agent(model=model),
        "guardian": lambda: create_guardian_agent(model=model),
        "sovereign": lambda: create_cortex_swarm(model=model),
    }

    agent = agent_map[agent_name]()
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="cortex", session_service=session_service)

    print(f"\n🧠 CORTEX ADK — {agent.name}")
    print(f"   Model: {agent.model}")
    print(f"   Type 'quit' to exit\n")

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


def run_web(port: int = 8000) -> None:
    """Launch the ADK web dev UI."""
    try:
        from google.adk.cli import cli_tools_click

        sys.argv = ["adk", "web", "--port", str(port)]
        cli_tools_click.main()
    except ImportError:
        logger.error("Google ADK not installed. Install with: pip install google-adk")
        sys.exit(1)


def main() -> None:
    """Entry point for the ADK runner."""
    args = _parse_args()

    if args.web:
        run_web(port=args.port)
    else:
        run_cli(agent_name=args.agent, model=args.model)


if __name__ == "__main__":
    main()
