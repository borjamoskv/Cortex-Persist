#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from cortex.extensions.mcp.claude_tool import run_claude_query


def main():
    parser = argparse.ArgumentParser(description="C5-REAL Claude Opus Dispatcher")
    parser.add_argument("prompt", help="Prompt to send to Claude")
    parser.add_argument(
        "--model", default="claude-3-opus-20240229", help="Model ID (e.g. claude-3-opus-20240229)"
    )

    args = parser.parse_args()

    result = run_claude_query(args.prompt, args.model)
    sys.stdout.write(result + "\n")


if __name__ == "__main__":
    main()
