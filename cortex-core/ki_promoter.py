#!/usr/bin/env python3
"""
KI Context Promoter — Smart KI selection for CORTEX-Persist.

Replaces blind LRU with context-aware scoring.
Analyzes current working context (project, git branch, open files) and
"promotes" the most relevant KIs by reading their metadata, which updates
the platform's internal last_accessed tracking.

Scoring function:
  score = tag_relevance × 0.5 + domain_match × 0.3 + freshness × 0.2

Usage:
  python3 ki_promoter.py                          # auto-detect context
  python3 ki_promoter.py --project cortex         # explicit project
  python3 ki_promoter.py --domain security        # force domain
  python3 ki_promoter.py --tags bounty,immunefi   # force tags
  python3 ki_promoter.py --top 25                 # promote top-25 (default: 20)
  python3 ki_promoter.py --dry-run                # show scores without promoting
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field

KI_BASE = Path.home() / ".gemini" / "antigravity" / "knowledge"

# Project → relevant tags/domains mapping
PROJECT_CONTEXT = {
    "cortex-persist": {
        "tags": {"cortex", "ai-agent", "persistence", "infrastructure"},
        "domain": "cortex",
    },
    "cortex": {
        "tags": {"cortex", "ai-agent", "research", "infrastructure"},
        "domain": "cortex",
    },
    "bounty": {
        "tags": {"bounty", "immunefi", "security", "web3", "critical", "high"},
        "domain": "security",
    },
    "music": {
        "tags": {"music", "sonic", "audio", "mastering"},
        "domain": "multimedia",
    },
    "systemforge": {
        "tags": {"infrastructure", "macos", "system"},
        "domain": "infrastructure",
    },
}

# Universal high-value KIs that should always rank well
ALWAYS_RELEVANT_TAGS = {"cortex", "c5-real", "2026"}


@dataclass
class ScoredKI:
    name: str
    path: Path
    score: float
    tag_score: float
    domain_score: float
    freshness_score: float
    domain: str = ""
    tags: list = field(default_factory=list)
    summary_preview: str = ""


def detect_context() -> dict:
    """Auto-detect current working context from environment."""
    context = {"tags": set(), "domain": "general", "project": "unknown"}

    # Check git repo name
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            project_name = Path(result.stdout.strip()).name.lower()
            context["project"] = project_name

            # Match against known projects
            for key, ctx in PROJECT_CONTEXT.items():
                if key in project_name:
                    context["tags"] = ctx["tags"]
                    context["domain"] = ctx["domain"]
                    break
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check for active file hints from environment
    active_file = os.environ.get("CORTEX_ACTIVE_FILE", "")
    if "bounty" in active_file.lower() or "immunefi" in active_file.lower():
        context["domain"] = "security"
        context["tags"].update({"bounty", "security", "immunefi"})
    elif "persistence" in active_file.lower() or "cortex" in active_file.lower():
        context["domain"] = "cortex"
        context["tags"].update({"cortex", "ai-agent"})

    # Always include universal tags
    context["tags"].update(ALWAYS_RELEVANT_TAGS)

    return context


def score_ki(meta: dict, meta_path: Path, context: dict) -> ScoredKI:
    """Score a KI based on relevance to current context."""
    ki_tags = set(t.lower() for t in meta.get("tags", []))
    ki_domain = meta.get("domain", "general").lower()
    ctx_tags = set(t.lower() for t in context.get("tags", set()))
    ctx_domain = context.get("domain", "general").lower()

    # Tag relevance: Jaccard-like overlap
    if ctx_tags:
        tag_overlap = len(ki_tags & ctx_tags)
        tag_score = min(tag_overlap / max(len(ctx_tags), 1), 1.0)
    else:
        tag_score = 0.0

    # Domain match: binary with partial credit
    if ki_domain == ctx_domain:
        domain_score = 1.0
    elif ki_domain in ("cortex", "ai") and ctx_domain in ("cortex", "ai"):
        domain_score = 0.7
    elif ki_domain in ("security", "web3") and ctx_domain in ("security", "web3"):
        domain_score = 0.7
    else:
        domain_score = 0.0

    # Freshness: decay from last_accessed
    freshness_score = 0.0
    la = meta.get("last_accessed") or meta.get("updated_at") or meta.get("created_at")
    if la:
        try:
            if la.endswith("Z"):
                la_dt = datetime.fromisoformat(la.replace("Z", "+00:00"))
            elif "+" in la or la.count("-") > 2:
                la_dt = datetime.fromisoformat(la)
            else:
                la_dt = datetime.fromisoformat(la + "+00:00")

            age_hours = (datetime.now(timezone.utc) - la_dt).total_seconds() / 3600
            # Exponential decay: half-life = 168h (1 week)
            freshness_score = 2 ** (-age_hours / 168)
        except (ValueError, TypeError):
            freshness_score = 0.1

    # Weighted composite
    score = (tag_score * 0.5) + (domain_score * 0.3) + (freshness_score * 0.2)

    # Bonus: access_count (frequency boost)
    access_count = meta.get("access_count", 0)
    if access_count > 5:
        score *= 1.1
    if access_count > 20:
        score *= 1.1

    summary = meta.get("summary", "")
    preview = summary[:80] + "…" if len(summary) > 80 else summary

    return ScoredKI(
        name=meta_path.parent.name,
        path=meta_path,
        score=round(score, 4),
        tag_score=round(tag_score, 3),
        domain_score=round(domain_score, 3),
        freshness_score=round(freshness_score, 3),
        domain=ki_domain,
        tags=list(ki_tags)[:5],
        summary_preview=preview,
    )


def promote_ki(ki: ScoredKI):
    """
    'Promote' a KI by reading its metadata file.

    This triggers the platform's internal access tracking,
    updating last_accessed so it gets selected for injection.
    """
    # Read the file — this is the promotion mechanism
    with open(ki.path) as f:
        _ = json.load(f)

    # Also update last_accessed in the metadata itself
    with open(ki.path) as f:
        meta = json.load(f)

    meta["last_accessed"] = datetime.now(timezone.utc).isoformat()
    meta["access_count"] = meta.get("access_count", 0) + 1

    with open(ki.path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    top_n = 20

    # Parse arguments
    context = None
    for i, arg in enumerate(args):
        if arg == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1])
        elif arg == "--domain" and i + 1 < len(args):
            context = context or detect_context()
            context["domain"] = args[i + 1]
        elif arg == "--tags" and i + 1 < len(args):
            context = context or detect_context()
            context["tags"].update(args[i + 1].split(","))
        elif arg == "--project" and i + 1 < len(args):
            project = args[i + 1].lower()
            for key, ctx in PROJECT_CONTEXT.items():
                if key in project:
                    context = {"tags": ctx["tags"], "domain": ctx["domain"], "project": project}
                    context["tags"].update(ALWAYS_RELEVANT_TAGS)
                    break

    if context is None:
        context = detect_context()

    print(f"{'=' * 70}")
    print("KI CONTEXT PROMOTER")
    print(f"{'=' * 70}")
    print(f"  Project:  {context.get('project', '?')}")
    print(f"  Domain:   {context['domain']}")
    print(f"  Tags:     {', '.join(sorted(context['tags']))}")
    print(f"  Top-N:    {top_n}")
    print(f"  Mode:     {'DRY-RUN' if dry_run else 'PROMOTE'}")
    print()

    # Score all KIs
    scored = []
    for ki_dir in KI_BASE.iterdir():
        meta_path = ki_dir / "metadata.json"
        if not meta_path.is_file():
            continue
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            scored.append(score_ki(meta, meta_path, context))
        except (OSError, json.JSONDecodeError):
            continue

    # Sort by score descending
    scored.sort(key=lambda x: x.score, reverse=True)

    # Display rankings
    print(f"{'#':<4} {'Score':<8} {'Tag':<6} {'Dom':<6} {'Fresh':<7} {'Domain':<15} {'Name'}")
    print(f"{'─' * 4} {'─' * 8} {'─' * 6} {'─' * 6} {'─' * 7} {'─' * 15} {'─' * 40}")

    for i, ki in enumerate(scored[:top_n]):
        marker = "→" if not dry_run else " "
        print(
            f"{marker}{i + 1:<3} {ki.score:<8.4f} {ki.tag_score:<6.3f} "
            f"{ki.domain_score:<6.3f} {ki.freshness_score:<7.3f} "
            f"{ki.domain:<15} {ki.name[:40]}"
        )

    # Show what's being demoted
    if len(scored) > top_n:
        demoted_with_score = [ki for ki in scored[top_n:] if ki.score > 0]
        if demoted_with_score:
            print(f"\n  ⚠ {len(demoted_with_score)} KIs with score > 0 NOT promoted")

    # Promote if not dry-run
    if not dry_run:
        promoted = 0
        for ki in scored[:top_n]:
            try:
                promote_ki(ki)
                promoted += 1
            except OSError as e:
                print(f"  ERROR promoting {ki.name}: {e}")

        print(f"\n  ✓ Promoted {promoted}/{top_n} KIs")
        print("  → These will be injected in the next conversation")
    else:
        print(f"\n  → Run without --dry-run to promote top-{top_n}")

    # Bottom 10 for awareness
    print("\n  Bottom 5 (lowest relevance):")
    for ki in scored[-5:]:
        print(f"    {ki.score:.4f}  {ki.domain:<15} {ki.name[:50]}")


if __name__ == "__main__":
    main()
