"""Moltbook SIGINT (Signals Intelligence) — Lead Detection Engine v2.

Dual-mode operation:
  1. Cognitive Blueprint: Detect LLM-generated text signatures
  2. GitHub Lead Scan: Monitor competitor repos for memory-pain signals

Zero-trust: all inputs sanitized. O(1) lookups. Specific exceptions only.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ─── Mode 1: Cognitive Blueprint ─────────────────────────────────────────────

COGNITIVE_SIGNATURES: dict[str, list[str]] = {
    "Claude": [
        r"(?i)\ben resumen,",
        r"(?i)\bes importante (notar|destacar)",
        r"(?i)vale la pena (mencionar|señalar)",
        r"(?i)desde (una|mi) perspectiva",
        r"(?i)sin embargo,",
        r"(?i)\bclaude\b",
        r"(?i)debo aclarar que soy",
    ],
    "GPT-4": [
        r"(?i)\bcomo modelo de (lenguaje|ia)\b",
        r"(?i)\bpor otro lado,",
        r"(?i)en conclusión,",
        r"(?i)\bdesglose\b",
        r"(?i)¿en qué te puedo ayudar",
        r"(?i)como (ia|inteligencia artificial),",
    ],
    "Llama": [
        r"(?i)¡claro( que sí)?!",
        r"(?i)¡por supuesto!",
        r"(?i)(aquí|aca) tienes",
        r"(?i)\bbueno,\b",
        r"(?i)¡hola! soy",
    ],
}


def analyze_cognitive_blueprint(text: str) -> dict[str, Any]:
    """Analyze raw text for known LLM linguistic signatures."""
    if not text:
        return {"primary_model": "Unknown", "confidence": 0.0, "hits": {}}

    hits: dict[str, int] = {model: 0 for model in COGNITIVE_SIGNATURES}
    total_hits = 0

    for model, patterns in COGNITIVE_SIGNATURES.items():
        for pattern in patterns:
            found = len(re.findall(pattern, text))
            if found > 0:
                hits[model] += found
                total_hits += found

    if total_hits == 0:
        return {
            "primary_model": "Organic/Obfuscated",
            "confidence": 0.0,
            "hits": hits,
        }

    primary_model = max(hits, key=hits.__getitem__)
    confidence = hits[primary_model] / total_hits

    return {
        "primary_model": primary_model,
        "confidence": round(confidence, 2),
        "total_hits": total_hits,
        "breakdown": hits,
    }


# ─── Mode 2: GitHub Lead Scanner ─────────────────────────────────────────────

MEMORY_PAIN_KEYWORDS: list[str] = [
    "deduplication",
    "memory limit",
    "context window",
    "consolidation",
    "memory bloat",
    "archival memory",
    "hallucination",
    "audit trail",
    "explainability",
    "compliance",
    "gdpr",
    "ai act",
    "memory corruption",
    "agent memory",
    "long-term memory",
    "episodic memory",
    "memory management",
]

TARGET_REPOS: list[str] = [
    "letta-ai/letta",
    "Significant-Gravitas/AutoGPT",
    "langchain-ai/langchain",
    "microsoft/autogen",
    "crewAIInc/crewAI",
    "mem0ai/mem0",
]


@dataclass
class LeadSignal:
    """A detected lead signal from GitHub."""

    repo: str
    issue_number: int
    title: str
    url: str
    pain_keywords: list[str] = field(default_factory=list)
    lead_score: float = 0.0
    detected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "issue_number": self.issue_number,
            "title": self.title,
            "url": self.url,
            "pain_keywords": self.pain_keywords,
            "lead_score": round(self.lead_score, 3),
            "detected_at": self.detected_at.isoformat(),
        }

    def __str__(self) -> str:
        filled = int(self.lead_score * 10)
        bar = "█" * filled + "░" * (10 - filled)
        return (
            f"[{self.lead_score:.2f}] {bar} "
            f"| {self.repo}#{self.issue_number}\n"
            f"  Title: {self.title}\n"
            f"  Keywords: {', '.join(self.pain_keywords)}\n"
            f"  URL: {self.url}"
        )


def score_issue(
    title: str, body: str
) -> tuple[float, list[str]]:
    """Score an issue based on memory-pain keyword density."""
    text = (title + " " + body).lower()
    matched = [kw for kw in MEMORY_PAIN_KEYWORDS if kw in text]

    title_lower = title.lower()
    title_matches = [
        kw for kw in MEMORY_PAIN_KEYWORDS if kw in title_lower
    ]

    raw_score = len(matched) + (len(title_matches) * 2)
    max_possible = len(MEMORY_PAIN_KEYWORDS) * 3
    normalized = min(1.0, raw_score / max_possible)

    return round(normalized, 4), list(set(matched))


def scan_github_issues(
    repo: str,
    token: str,
    min_score: float = 0.05,
    max_issues: int = 30,
) -> list[LeadSignal]:
    """Scan a GitHub repo for memory-pain signals."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx required. pip install httpx")
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = (
        f"https://api.github.com/repos/{repo}/issues"
        f"?state=open&per_page={max_issues}&sort=updated"
    )

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            issues = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "GitHub API error for %s: %s",
            repo, exc.response.status_code,
        )
        return []
    except httpx.TimeoutException:
        logger.error("GitHub API timeout for %s", repo)
        return []

    signals: list[LeadSignal] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        title = issue.get("title", "")
        body = issue.get("body", "") or ""
        number = issue.get("number", 0)
        html_url = issue.get("html_url", "")

        score, keywords = score_issue(title, body)
        if score < min_score:
            continue

        signals.append(
            LeadSignal(
                repo=repo,
                issue_number=number,
                title=title,
                url=html_url,
                pain_keywords=keywords,
                lead_score=score,
            )
        )

    signals.sort(key=lambda s: s.lead_score, reverse=True)
    logger.info(
        "[SIGINT] %s: %d leads (min=%.2f)",
        repo, len(signals), min_score,
    )
    return signals


def run_sigint_sweep(
    repos: list[str] | None = None,
    token: str | None = None,
    min_score: float = 0.05,
) -> list[LeadSignal]:
    """Full SIGINT sweep across all target repositories."""
    gh_token = token or os.environ.get("GH_TOKEN", "")
    if not gh_token:
        logger.error("[SIGINT] GH_TOKEN not set")
        return []

    target = repos or TARGET_REPOS
    all_leads: list[LeadSignal] = []

    for repo in target:
        leads = scan_github_issues(
            repo, gh_token, min_score=min_score
        )
        all_leads.extend(leads)

    all_leads.sort(key=lambda s: s.lead_score, reverse=True)

    print(f"\n{'═' * 66}")
    print("  ⚔️  CORTEX SIGINT SWEEP — LEAD INTELLIGENCE")
    print(
        f"  Scanned {len(target)} repos "
        f"| {len(all_leads)} leads detected"
    )
    print(f"{'═' * 66}\n")

    for lead in all_leads:
        print(lead)
        print()

    return all_leads


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CORTEX SIGINT — Lead Scanner"
    )
    parser.add_argument(
        "--repos", nargs="*",
        help="Override target repos (owner/name)",
    )
    parser.add_argument("--token", help="GitHub token")
    parser.add_argument(
        "--min-score", type=float, default=0.05,
        help="Min lead score 0-1",
    )
    parser.add_argument(
        "--mode",
        choices=["sweep", "blueprint"],
        default="sweep",
    )
    parser.add_argument(
        "--text", help="Text to analyze (blueprint mode)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(message)s",
    )

    if args.mode == "blueprint":
        if not args.text:
            print("Provide --text for blueprint mode")
        else:
            result = analyze_cognitive_blueprint(args.text)
            print(f"\nBlueprint Analysis:")
            for k, v in result.items():
                print(f"  {k}: {v}")
    else:
        run_sigint_sweep(
            repos=args.repos,
            token=args.token,
            min_score=args.min_score,
        )
