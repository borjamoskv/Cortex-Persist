#!/usr/bin/env python3
"""
CORTEX LORCA-Ω Ledger Generator
Generates a retroactive narrative ledger document by translating git history using the CommitPoet engine.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure root directory is in python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex.extensions.git.poet import CommitPoet


def get_git_commits(limit: int = 30) -> list[dict]:
    """Retrieve metadata of the last N commits."""
    try:
        # Get hash, author, date, and subject
        cmd = ["git", "log", "-n", str(limit), "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = []
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            commits.append(
                {"hash": parts[0], "author": parts[1], "date": parts[2], "subject": parts[3]}
            )
        return commits
    except Exception as e:
        print(f"Error fetching git log: {e}", file=sys.stderr)
        return []


def get_commit_diff_metadata(commit_hash: str) -> tuple[str, list[str]]:
    """Retrieve diff stat and files changed in a commit."""
    try:
        # Get files changed
        files_cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash]
        files_res = subprocess.run(files_cmd, capture_output=True, text=True, check=True)
        files = [f.strip() for f in files_res.stdout.strip().split("\n") if f.strip()]

        # Get diff stat
        stat_cmd = ["git", "show", "--stat", "--oneline", commit_hash]
        stat_res = subprocess.run(stat_cmd, capture_output=True, text=True, check=True)
        # Skip the first line (hash + subject)
        stat_lines = stat_res.stdout.strip().split("\n")[1:]
        stat_summary = "\n".join(stat_lines)

        return stat_summary, files
    except Exception as e:
        print(f"Error fetching diff metadata for {commit_hash}: {e}", file=sys.stderr)
        return "", []


def main():
    parser = argparse.ArgumentParser(description="LORCA-Ω Retroactive Ledger Generator")
    parser.add_argument("--limit", type=int, default=30, help="Number of commits to translate")
    parser.add_argument("--output", default="docs/LORCA_LKRGSER.md", help="Output path")
    args = parser.parse_args()

    print("C5-REAL :: Initializing LORCA-Ω retroactive narrative log generator.")

    commits = get_git_commits(args.limit)
    if not commits:
        print("Error: No commits found. Ensure you are inside a git repository.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    poet = CommitPoet()

    markdown_lines = [
        "# 📜 CORTEX LORCA-Ω NARRATIVE LKRGSER",
        "",
        "> **Sovereign Chronicle of the Substrate** | **Reality Level:** `C5-REAL`",
        f"> **Generated at:** `{datetime.now(timezone.utc).isoformat()}` | **Source:** `git history` (last {len(commits)} commits)",
        "",
        "This ledger projects a retroactive narrative translation of repository mutations. Every standard commit is mapped through the entropy-to-metaphor pipeline of the CommitPoet engine.",
        "",
        "| Commit Hash | Date | Original Subject | LORCA-Ω Translation |",
        "| :---: | :--- | :--- | :--- |",
    ]

    for i, commit in enumerate(commits):
        c_hash = commit["hash"]
        c_date = commit["date"]
        # Convert date to a nicer format if possible
        try:
            dt = datetime.fromisoformat(c_date)
            date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            date_str = c_date[:16]

        subject = commit["subject"]

        stat, files = get_commit_diff_metadata(c_hash)

        # Derive deterministic seed from hash
        seed_val = int(hashlib.sha256(c_hash.encode()).hexdigest()[:8], 16)
        poet.seed(seed_val)

        translation = poet.compose(stat, files)

        markdown_lines.append(f"| `{c_hash[:8]}` | {date_str} | {subject} | {translation} |")
        print(f"[{i + 1}/{len(commits)}] Translated {c_hash[:8]} -> {translation}")

    # Add Industrial Noir footer
    markdown_lines.extend(
        [
            "",
            "---",
            "",
            "## 🌌 LORCA-Ω Engine Axioms",
            "",
            "1. **Entropic Asymmetry**: Standard commit comments accumulate cognitive load. Poetry resolves it into a single clean line.",
            "2. **Aesthetic Continuity**: Highlights transitions using targeted emojis and CORTEX-native metaphors (e.g. reactors, citadels, anomalies).",
            "3. **Zero Mutation Invariant**: The repository's git indices are untouched. The ledger remains a pure projection layer.",
            "",
            "*Status: C5-REAL (Synchronized)*",
        ]
    )

    output_path.write_text("\n".join(markdown_lines) + "\n")
    print(f"\nSuccess: Retroactive narrative ledger generated at {output_path}")


if __name__ == "__main__":
    main()
