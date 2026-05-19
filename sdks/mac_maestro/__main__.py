"""Mac-Maestro-Ω CLI — Sovereign macOS Automation Tool.

Usage:
    python3 -m mac_maestro inspect --app com.apple.TextEdit
    python3 -m mac_maestro click --app com.apple.TextEdit --role AXButton --title Save
    python3 -m mac_maestro type --app com.apple.TextEdit --text "Hello World"
    python3 -m mac_maestro key --app com.apple.TextEdit --key "cmd+s"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .models import UIAction


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ─── Subcommands ──────────────────────────────────────────────────


def cmd_inspect(args: argparse.Namespace) -> int:
    """Dump the AX tree of a running application."""
    from .app_discovery import get_pid
    from .ax_inspector import inspect_app

    pid = get_pid(args.app)
    print(f"PID: {pid}")

    snapshot = inspect_app(pid)
    _print_tree(snapshot, indent=0, max_depth=args.depth)
    return 0


def _print_tree(node, indent: int, max_depth: int) -> None:
    """Print AX tree in a readable format."""
    prefix = "  " * indent
    parts = []
    if node.role:
        parts.append(node.role)
    if node.title:
        parts.append(f'"{node.title}"')
    if node.identifier:
        parts.append(f"id={node.identifier}")
    if node.description:
        parts.append(f"desc={node.description}")
    if node.position and node.size:
        parts.append(
            f"@({node.position[0]:.0f},{node.position[1]:.0f})"
            f" {node.size[0]:.0f}x{node.size[1]:.0f}"
        )
    if node.enabled is False:
        parts.append("[disabled]")

    label = " ".join(parts) if parts else "(empty)"
    print(f"{prefix}{label}")

    for child in node.children:
        _print_tree(child, indent + 1, max_depth)


def cmd_click(args: argparse.Namespace) -> int:
    """Click a UI element by semantic query."""
    from .workflow import MacMaestroWorkflow

    query: dict[str, str] = {}
    if args.role:
        query["role"] = args.role
    if args.title:
        query["title"] = args.title
    if args.description:
        query["description"] = args.description
    if args.identifier:
        query["identifier"] = args.identifier

    if not query:
        print(
            "ERROR: At least one of --role, --title, --description, --identifier is required.",
            file=sys.stderr,
        )
        return 1

    action = UIAction(
        name=f"cli_click_{args.title or args.role or 'element'}",
        vector="D",
        target_query=query,
        idempotent=True,
        retry_limit=2,
    )

    wf = MacMaestroWorkflow(args.app)
    wf.execute_action(action)
    print(f"OK: clicked element matching {json.dumps(query)}")
    return 0


def cmd_type(args: argparse.Namespace) -> int:
    """Type text into the frontmost application."""
    from .keyboard import type_text
    from .workflow import MacMaestroWorkflow

    action = UIAction(
        name="cli_type",
        vector="C",
        target_query={},
        executor=lambda: type_text(args.text),
        idempotent=True,
        retry_limit=1,
    )

    wf = MacMaestroWorkflow(args.app)
    wf.execute_action(action)
    print(f"OK: typed {len(args.text)} characters")
    return 0


def cmd_key(args: argparse.Namespace) -> int:
    """Send a keyboard shortcut."""
    from .keyboard import press_key
    from .workflow import MacMaestroWorkflow

    action = UIAction(
        name=f"cli_key_{args.key}",
        vector="C",
        target_query={},
        executor=lambda: press_key(args.key),
        idempotent=True,
        retry_limit=1,
    )

    wf = MacMaestroWorkflow(args.app)
    wf.execute_action(action)
    print(f"OK: sent key '{args.key}'")
    return 0


# ─── Parser ───────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mac_maestro",
        description="Mac-Maestro-Ω: Sovereign macOS Automation Tool",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── inspect ──
    p_inspect = sub.add_parser(
        "inspect",
        help="Dump the AX tree of a running app",
    )
    p_inspect.add_argument("--app", "-a", required=True, help="Bundle ID")
    p_inspect.add_argument(
        "--depth",
        "-d",
        type=int,
        default=8,
        help="Max tree depth (default: 8)",
    )

    # ── click ──
    p_click = sub.add_parser(
        "click",
        help="Click a UI element by semantic query",
    )
    p_click.add_argument("--app", "-a", required=True, help="Bundle ID")
    p_click.add_argument("--role", "-r", help="AX role (e.g. AXButton)")
    p_click.add_argument("--title", "-t", help="Element title")
    p_click.add_argument("--description", help="Element description")
    p_click.add_argument("--identifier", "-i", help="Element identifier")

    # ── type ──
    p_type = sub.add_parser("type", help="Type text into focused element")
    p_type.add_argument("--app", "-a", required=True, help="Bundle ID")
    p_type.add_argument("text", help="Text to type")

    # ── key ──
    p_key = sub.add_parser("key", help="Send a keyboard shortcut")
    p_key.add_argument("--app", "-a", required=True, help="Bundle ID")
    p_key.add_argument("key", help="Key combo (e.g. 'cmd+s', 'return')")

    return parser


# ─── Main ─────────────────────────────────────────────────────────


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(args.verbose)

    dispatch = {
        "inspect": cmd_inspect,
        "click": cmd_click,
        "type": cmd_type,
        "key": cmd_key,
    }

    try:
        return dispatch[args.command](args)
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
