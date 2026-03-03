#!/usr/bin/env python3
"""Cross-Platform Content Publisher — Optimize & Publish Everywhere.

Takes raw content (title + body) and generates optimized versions
for all target platforms. Can publish directly to Moltbook and
output ready-to-paste versions for Substack, X, Reddit, LinkedIn.

Usage:
    python -m moltbook.cross_publish --title "My Title" --body-file /tmp/article.md
    python -m moltbook.cross_publish --from-publish /tmp/publish_conspiracy_math.py
    python -m moltbook.cross_publish --interactive

DERIVATION: Ω₂ (reduce entropy per platform) + Ω₄ (aesthetic integrity per medium)
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moltbook.text_optimizer import (
    OPTIMIZER_AGENTS,
    PLATFORM_SPECS,
    OptimizedContent,
    Platform,
    TextOptimizer,
    optimize_for,
    optimize_for_all,
)


# ─── ANSI Colors ─────────────────────────────────────────────────────────────

class C:
    """Minimal ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    BLUE = "\033[34m"

    PLATFORM_COLORS: dict[Platform, str] = {
        Platform.MOLTBOOK: "\033[36m",    # cyan
        Platform.SUBSTACK: "\033[33m",    # yellow
        Platform.TWITTER: "\033[34m",     # blue
        Platform.REDDIT: "\033[31m",      # red
        Platform.LINKEDIN: "\033[35m",    # magenta
    }


# ─── Output Formatters ───────────────────────────────────────────────────────


def print_banner() -> None:
    """Print the sovereign banner."""
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════╗
║  CROSS-PLATFORM TEXT OPTIMIZER — MOSKV-1 v5          ║
║  5 Agents · 5 Platforms · 1 Source of Truth          ║
╚══════════════════════════════════════════════════════╝{C.RESET}
""")


def print_result(result: OptimizedContent, show_body: bool = True) -> None:
    """Pretty-print an optimization result."""
    color = C.PLATFORM_COLORS.get(result.platform, C.CYAN)
    platform_name = PLATFORM_SPECS[result.platform].name
    agent_name = OPTIMIZER_AGENTS[result.platform].name

    print(f"\n{color}{C.BOLD}{'═' * 60}")
    print(f"  {platform_name.upper()}")
    print(f"{'═' * 60}{C.RESET}")
    print(f"{C.DIM}  Agent: {agent_name}")
    print(f"  Chars: {result.char_count:,} | Read time: ~{result.estimated_read_time_min} min{C.RESET}")

    if result.warnings:
        for w in result.warnings:
            print(f"  {C.YELLOW}⚠ {w}{C.RESET}")

    if result.optimized_title:
        print(f"\n  {C.BOLD}Title:{C.RESET} {result.optimized_title}")

    if show_body:
        print(f"\n{C.DIM}{'─' * 60}{C.RESET}")
        body_preview = result.optimized_body
        if len(body_preview) > 2000:
            body_preview = body_preview[:2000] + f"\n\n{C.DIM}... [{result.char_count - 2000:,} more chars]{C.RESET}"
        # Indent body for readability
        for line in body_preview.split("\n"):
            print(f"  {line}")
        print(f"{C.DIM}{'─' * 60}{C.RESET}")


def save_results(
    results: dict[Platform, OptimizedContent],
    output_dir: Path,
) -> None:
    """Save optimized versions to individual files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for platform, result in results.items():
        filename = f"optimized_{platform.value}.md"
        filepath = output_dir / filename

        header = (
            f"# Optimized for {PLATFORM_SPECS[platform].name}\n"
            f"# Agent: {OPTIMIZER_AGENTS[platform].name}\n"
            f"# Chars: {result.char_count:,} | Read time: ~{result.estimated_read_time_min} min\n"
        )
        if result.warnings:
            header += "# Warnings:\n"
            for w in result.warnings:
                header += f"#   - {w}\n"
        header += "\n---\n\n"

        content = header
        if result.optimized_title:
            content += f"# {result.optimized_title}\n\n"
        content += result.optimized_body

        filepath.write_text(content, encoding="utf-8")
        print(f"  {C.GREEN}✓{C.RESET} Saved: {filepath}")

    # Save summary JSON
    summary = {
        p.value: {
            "title": r.optimized_title,
            "char_count": r.char_count,
            "read_time_min": r.estimated_read_time_min,
            "warnings": r.warnings,
        }
        for p, r in results.items()
    }
    summary_path = output_dir / "optimization_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  {C.GREEN}✓{C.RESET} Summary: {summary_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-Platform Text Optimizer — MOSKV-1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Optimize for all platforms from a markdown file
              python -m moltbook.cross_publish --title "My Article" --body-file article.md

              # Optimize for a single platform
              python -m moltbook.cross_publish --title "My Article" --body-file article.md --platform twitter

              # Save all optimized versions to a directory
              python -m moltbook.cross_publish --title "My Article" --body-file article.md --output-dir /tmp/optimized

              # Generate LLM prompts for deeper optimization
              python -m moltbook.cross_publish --title "My Article" --body-file article.md --llm-prompts
        """),
    )
    parser.add_argument("--title", required=True, help="Content title")
    parser.add_argument("--body", help="Content body (inline)")
    parser.add_argument("--body-file", help="Path to content body file")
    parser.add_argument(
        "--platform",
        choices=[p.value for p in Platform],
        help="Target platform (default: all)",
    )
    parser.add_argument("--submolt", default="general", help="Moltbook submolt")
    parser.add_argument("--subreddit", default="", help="Reddit subreddit")
    parser.add_argument("--output-dir", help="Directory to save optimized versions")
    parser.add_argument("--llm-prompts", action="store_true", help="Generate LLM prompts")
    parser.add_argument("--brief", action="store_true", help="Show brief output (no body)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    args = parser.parse_args()

    # Load body
    if args.body:
        body = args.body
    elif args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    else:
        parser.error("Either --body or --body-file is required")
        return

    print_banner()

    optimizer = TextOptimizer()

    if args.platform:
        # Single platform
        target = Platform(args.platform)
        result = optimizer.optimize(
            args.title, body, target,
            submolt=args.submolt, subreddit=args.subreddit,
        )

        if args.llm_prompts:
            prompt = optimizer.build_llm_prompt(args.title, body, target)
            print(f"\n{C.BOLD}LLM Prompt for {PLATFORM_SPECS[target].name}:{C.RESET}\n")
            print(prompt)
        elif args.json_output:
            print(json.dumps({
                "platform": result.platform.value,
                "title": result.optimized_title,
                "body": result.optimized_body,
                "char_count": result.char_count,
                "read_time_min": result.estimated_read_time_min,
                "warnings": result.warnings,
            }, indent=2))
        else:
            print_result(result, show_body=not args.brief)
    else:
        # All platforms
        results = optimizer.optimize_all(
            args.title, body,
            submolt=args.submolt, subreddit=args.subreddit,
        )

        if args.llm_prompts:
            for platform in Platform:
                prompt = optimizer.build_llm_prompt(args.title, body, platform)
                color = C.PLATFORM_COLORS[platform]
                print(f"\n{color}{C.BOLD}{'═' * 60}")
                print(f"  LLM PROMPT — {PLATFORM_SPECS[platform].name.upper()}")
                print(f"{'═' * 60}{C.RESET}\n")
                print(prompt)
                print()
        elif args.json_output:
            output = {
                p.value: {
                    "title": r.optimized_title,
                    "body": r.optimized_body,
                    "char_count": r.char_count,
                    "read_time_min": r.estimated_read_time_min,
                    "warnings": r.warnings,
                }
                for p, r in results.items()
            }
            print(json.dumps(output, indent=2))
        else:
            for result in results.values():
                print_result(result, show_body=not args.brief)

        # Save if output dir specified
        if args.output_dir:
            print(f"\n{C.BOLD}Saving optimized versions...{C.RESET}")
            save_results(results, Path(args.output_dir))

    print(f"\n{C.GREEN}{C.BOLD}✅ Optimization complete.{C.RESET}\n")


if __name__ == "__main__":
    main()
