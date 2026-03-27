#!/usr/bin/env python3
"""BOUNTY SCANNER — Sovereign Multi-Platform Capital Discovery Engine.

Platforms: Algora · Polar · Immunefi
Schedule:  Every 6 hours via launchd (see com.cortex.bounty_scanner.plist)
Output:    scripts/bounty_results/scan_<timestamp>.json
           CORTEX Ledger (if CORTEX_DB_PATH is set)

Thermodynamic filter (Ω₂):
  Exergy  = reward_usd (capital yield)
  Entropy = difficulty_weight × 50 + context_lines × 0.1
  Ratio   ≥ MIN_RATIO (default 3.0) → ACCEPTED

Confidence levels follow Ω₁ Byzantine Law.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("CORTEX_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("cortex.scanner.bounty")

# ─── Config ───────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
CORTEX_DB_PATH = os.getenv("CORTEX_DB_PATH", "")
MIN_REWARD_USD = float(os.getenv("SCANNER_MIN_REWARD", "100"))
MIN_RATIO = float(os.getenv("SCANNER_MIN_RATIO", "3.0"))

RESULTS_DIR = Path(__file__).parent / "bounty_results"
RESULTS_DIR.mkdir(exist_ok=True)

HTTP_TIMEOUT = httpx.Timeout(15.0)
# Immunefi: unofficial public mirror maintained at github raw — updated frequently
IMMUNEFI_API = "https://raw.githubusercontent.com/infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/main/projects.json"
# Algora: canonical domain (console.algora.io redirects here)
ALGORA_API = "https://algora.io/api/bounties"
# Polar: funded issues endpoint
POLAR_API = "https://api.polar.sh/v1/issues"


# ─── Data Models ──────────────────────────────────────────────────────────────
@dataclass
class BountyLead:
    platform: str
    title: str
    url: str
    reward_usd: float
    difficulty: str          # low | medium | high | critical
    tags: list[str] = field(default_factory=list)
    project: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    # Thermodynamic outputs — filled by evaluate()
    exergy: float = 0.0
    entropy: float = 0.0
    ratio: float = 0.0
    accepted: bool = False
    reject_reason: str = ""


# ─── Thermodynamic Evaluator (Ω₂ + Ω₉) ──────────────────────────────────────
def evaluate(lead: BountyLead) -> BountyLead:
    """Apply thermodynamic filter inline. Mutates lead in place."""
    diff_weight = {"low": 2, "medium": 5, "high": 8, "critical": 10}.get(lead.difficulty, 5)
    # [Ω₉] Context lines recalibration to prevent yield inflation fraud.
    # Immunefi audits require full protocol DAG traversal. Algora is scoped to issues.
    if lead.platform == "Immunefi":
        context_lines = 1500 if diff_weight <= 5 else (8000 if diff_weight <= 8 else 35000)
    else:
        context_lines = 150 if diff_weight <= 2 else (600 if diff_weight <= 5 else 2500)

    exergy = Decimal(str(lead.reward_usd))
    entropy_base = Decimal(diff_weight) * 50 + Decimal(context_lines) * Decimal("0.1")
    # Ghost vector penalty — if reward < $200 and high difficulty
    ghost_penalty = (
        Decimal(context_lines) * Decimal("0.5")
        if diff_weight >= 5 and exergy < Decimal("200")
        else Decimal("0")
    )
    # Metastability penalty — critical/high scope changes
    meta_penalty = (
        Decimal(diff_weight) ** 2 * Decimal("4")
        if diff_weight >= 8
        else Decimal("0")
    )

    entropy = max(entropy_base + ghost_penalty + meta_penalty, Decimal("1"))
    ratio = exergy / entropy

    lead.exergy = float(exergy)
    lead.entropy = float(entropy)
    lead.ratio = float(ratio)
    lead.accepted = ratio >= Decimal(str(MIN_RATIO))

    if not lead.accepted:
        lead.reject_reason = (
            f"ratio={ratio:.2f} < {MIN_RATIO} | "
            f"exergy={float(exergy):.0f} entropy={float(entropy):.0f}"
        )
    return lead


# ─── Platform Scrapers ────────────────────────────────────────────────────────

async def scan_algora(client: httpx.AsyncClient) -> list[BountyLead]:
    """Algora bounty discovery via GitHub Issues API.

    Algora's REST and GraphQL endpoints are not publicly accessible without
    authentication. We use the GitHub Issues search API instead, filtering
    for Algora-managed bounties by label patterns and body markers.
    This is the same dataset Algora surfaces on their web UI.
    """
    leads: list[BountyLead] = []
    # Algora-tagged issues: the label 'algora-bounty' or body contains algora.io links
    queries = [
        "label:algora-bounty is:issue is:open",
        "label:\"💎 Bounty\" is:issue is:open",  # Algora gem emoji label
        'algora in:body label:bounty is:issue is:open',
    ]
    seen_urls: set[str] = set()
    for query in queries:
        items = await _github_issue_search(client, query, limit=25)
        for item in items:
            html_url = item.get("html_url", "")
            if html_url in seen_urls:
                continue
            seen_urls.add(html_url)

            title = item.get("title", "")
            body = (item.get("body") or "")
            combined = title + " " + body
            reward = _parse_reward(combined)
            if reward < MIN_REWARD_USD:
                continue

            labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
            difficulty = _infer_difficulty(labels, reward)
            repo_m = re.search(r"github\.com/([^/]+/[^/]+)/issues", html_url)
            repo = repo_m.group(1) if repo_m else "unknown"
            leads.append(
                BountyLead(
                    platform="Algora",
                    title=title,
                    url=html_url,
                    reward_usd=reward,
                    difficulty=difficulty,
                    tags=labels,
                    project=repo,
                )
            )
        if len(leads) >= 30:
            break  # enough leads
    logger.info("[ALGORA] Raw leads: %d (min_reward=$%.0f)", len(leads), MIN_REWARD_USD)
    return leads


async def _github_issue_search(
    client: httpx.AsyncClient, query: str, limit: int = 30
) -> list[dict[str, Any]]:
    """GitHub search/issues API call, authenticated if GITHUB_TOKEN is set."""
    url = "https://api.github.com/search/issues"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": limit}
    try:
        r = await client.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as exc:
        logger.debug("[GITHUB] Search failed for query %r: %s", query[:60], exc)
        return []



async def scan_polar(client: httpx.AsyncClient) -> list[BountyLead]:
    """Polar.sh funded issues — GitHub label search (REST API deprecated 2025).

    Polar shut down its REST issue-funding endpoint; discovery now uses GitHub
    issue search for repos that still embed Polar funding badges.
    """
    import re as _re

    leads: list[BountyLead] = []
    gh_queries = [
        'label:"polar-bounty" is:issue is:open',
        'label:"💎 Bounty" is:issue is:open',
        'polar.sh in:body label:bounty is:issue is:open',
    ]
    gh_headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if gh_token := os.environ.get("GITHUB_TOKEN"):
        gh_headers["Authorization"] = f"Bearer {gh_token}"

    seen: set[str] = set()
    for q in gh_queries:
        try:
            r = await client.get(
                "https://api.github.com/search/issues",
                params={"q": q, "sort": "updated", "order": "desc", "per_page": "25"},
                headers=gh_headers,
                timeout=HTTP_TIMEOUT,
            )
            r.raise_for_status()
            for item in r.json().get("items", []):
                url = item.get("html_url", "")
                if url in seen:
                    continue
                seen.add(url)
                body = (item.get("body") or "").lower()
                m = _re.search(r"\$\s*([\d,]+)", body)
                reward = float(m.group(1).replace(",", "")) if m else MIN_REWARD_USD
                if reward < MIN_REWARD_USD:
                    reward = MIN_REWARD_USD
                title = item.get("title", "?")
                labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
                difficulty = _infer_difficulty(labels, reward)
                leads.append(
                    BountyLead(
                        platform="Polar",
                        title=title,
                        url=url,
                        reward_usd=reward,
                        difficulty=difficulty,
                        tags=labels,
                        project=item.get("repository_url", "").replace(
                            "https://api.github.com/repos/", ""
                        ),
                    )
                )
        except Exception as exc:
            logger.debug("[POLAR] GitHub query '%s' failed: %s", q, exc)

    if not leads:
        logger.warning("[POLAR] No polar-funded issues found via GitHub search")
    else:
        logger.info("[POLAR] Raw leads: %d", len(leads))
    return leads


async def scan_immunefi(client: httpx.AsyncClient) -> list[BountyLead]:
    """Immunefi bounty programs — uses public GitHub mirror JSON (updated ~daily).

    Primary:  infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial (GitHub raw)
    Fallback: pratraut snapshot mirror
    """
    IMMUNEFI_MIRRORS = [
        IMMUNEFI_API,  # infosec-us-team mirror
        "https://raw.githubusercontent.com/pratraut/Immunefi-Bug-Bounty-Programs-Snapshots/main/projects.json",
    ]
    leads: list[BountyLead] = []
    items: list[dict[str, Any]] = []
    for mirror in IMMUNEFI_MIRRORS:
        try:
            r = await client.get(mirror, timeout=HTTP_TIMEOUT, follow_redirects=True)
            r.raise_for_status()
            raw = r.json()
            # Mirror shape: list of project dicts or {"data": [...]}
            items = raw if isinstance(raw, list) else raw.get("data", raw.get("bounties", []))
            if items:
                logger.debug("[IMMUNEFI] Loaded %d programs from %s", len(items), mirror)
                break
        except Exception as exc:
            logger.debug("[IMMUNEFI] Mirror %s failed: %s", mirror, exc)
    if not items:
        logger.warning("[IMMUNEFI] All mirrors exhausted — no data")
        return []

    for item in items:
        # infosec-us-team mirror schema:
        #   maxBounty: int (USD), project: str, id: str (used in URL)
        #   rewards: list of tier dicts with {severity, fixedReward, maxReward}
        max_reward: float = 0.0

        # Primary: top-level maxBounty (most reliable single field)
        max_bounty_raw = item.get("maxBounty")
        if max_bounty_raw is not None:
            try:
                max_reward = float(str(max_bounty_raw).replace(",", ""))
            except (ValueError, TypeError):
                pass

        # Secondary: iterate tier rewards if maxBounty missing
        if max_reward == 0.0:
            for tier in (item.get("rewards") or []):
                for key in ("maxReward", "fixedReward", "value"):
                    val = tier.get(key)
                    if val is not None:
                        try:
                            max_reward = max(max_reward, float(str(val).replace(",", "")))
                        except (ValueError, TypeError):
                            pass

        if max_reward < MIN_REWARD_USD:
            continue

        name = item.get("project") or item.get("name", "?")
        # id field used in Immunefi URLs
        slug = item.get("id") or name.lower().replace(" ", "-")
        url = f"https://immunefi.com/bounty/{slug}/"
        difficulty = "critical" if max_reward >= 50_000 else "high"
        # ecosystems field in infosec mirror; fallback to tags
        ecosystems = [
            str(e) for e in (item.get("ecosystems") or item.get("tags") or [])
            if isinstance(e, (str, int))
        ]
        leads.append(
            BountyLead(
                platform="Immunefi",
                title=f"{name} — Bug Bounty",
                url=url,
                reward_usd=max_reward,
                difficulty=difficulty,
                tags=ecosystems,
                project=name,
            )
        )
    logger.info("[IMMUNEFI] Raw leads: %d", len(leads))
    return leads



# ─── Helpers ──────────────────────────────────────────────────────────────────
def _parse_reward(raw: Any) -> float:
    if raw is None:
        return 0.0
    s = str(raw).replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d{1,2})?)", s)
    return float(match.group(1)) if match else 0.0


def _infer_difficulty(labels: list[str], reward: float) -> str:
    joined = " ".join(str(l).lower() for l in labels)
    if any(k in joined for k in ("easy", "good first", "beginner", "starter")):
        return "low"
    if any(k in joined for k in ("medium", "intermediate")):
        return "medium"
    if any(k in joined for k in ("critical", "severity:critical", "critical-bug")):
        return "critical"
    # Fallback: infer from reward size
    if reward >= 10_000:
        return "critical"
    if reward >= 1_000:
        return "high"
    if reward >= 200:
        return "medium"
    return "low"


# ─── CORTEX Ledger Persistence ────────────────────────────────────────────────
async def persist_to_ledger(accepted: list[BountyLead]) -> None:
    """Persist accepted leads to CORTEX ledger if engine available (Ω₄)."""
    if not CORTEX_DB_PATH:
        logger.debug("[LEDGER] CORTEX_DB_PATH not set — skipping persistence.")
        return
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from cortex.cli.common import get_engine  # type: ignore[import]

        engine = get_engine()
        await engine.init_db()
        for lead in accepted:
            content = (
                f"[BountyScanner] {lead.platform} | {lead.title}\n"
                f"Reward: ${lead.reward_usd:.0f} | Ratio: {lead.ratio:.2f}\n"
                f"URL: {lead.url}"
            )
            await engine.store(
                project="cazarecompensas-agent",
                content=content,
                fact_type="scan_lead",
                tags=["bounty", "scan", lead.platform.lower()],
                confidence="C4",  # [Ω₁] API data is official documentation level (C4)
                source="scanner:bounty_scanner.py",
                meta={
                    "platform": lead.platform,
                    "reward_usd": lead.reward_usd,
                    "exergy": lead.exergy,
                    "entropy": lead.entropy,
                    "ratio": lead.ratio,
                    "url": lead.url,
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        logger.info("[LEDGER] Persisted %d accepted leads to CORTEX.", len(accepted))
    except Exception as exc:
        logger.error("[LEDGER] Persistence failed: %s", exc)


# ─── Main Scan Loop ───────────────────────────────────────────────────────────
async def run_scan() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    logger.info("=" * 60)
    logger.info("BOUNTY SCANNER — cycle %s", ts)
    logger.info("Platforms: Algora · Polar · Immunefi")
    logger.info("Min reward: $%.0f  |  Min ratio: %.1f", MIN_REWARD_USD, MIN_RATIO)
    logger.info("=" * 60)

    headers: dict[str, str] = {"Accept": "application/json", "User-Agent": "CORTEX-BountyScanner/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient(headers=headers) as client:
        algora_raw, polar_raw, immunefi_raw = await asyncio.gather(
            scan_algora(client),
            scan_polar(client),
            scan_immunefi(client),
            return_exceptions=False,
        )

    all_leads: list[BountyLead] = algora_raw + polar_raw + immunefi_raw

    # Thermodynamic evaluation
    for lead in all_leads:
        evaluate(lead)

    accepted = [l for l in all_leads if l.accepted]
    rejected = [l for l in all_leads if not l.accepted]

    # Sort accepted by ratio desc
    accepted.sort(key=lambda x: x.ratio, reverse=True)

    # ── Summary ──
    logger.info("")
    logger.info("─── SCAN RESULTS ────────────────────────────────────────────")
    logger.info("Total scanned : %d", len(all_leads))
    logger.info("  Algora      : %d", len(algora_raw))
    logger.info("  Polar       : %d", len(polar_raw))
    logger.info("  Immunefi    : %d", len(immunefi_raw))
    logger.info("Accepted (Ω₂): %d", len(accepted))
    logger.info("Rejected      : %d", len(rejected))
    logger.info("")

    if accepted:
        logger.info("── TOP 10 ACCEPTED BOUNTIES ─────────────────────────────────")
        for i, lead in enumerate(accepted[:10], 1):
            logger.info(
                "%2d. [%s] %s  $%.0f  ratio=%.2f",
                i,
                lead.platform,
                lead.title[:60],
                lead.reward_usd,
                lead.ratio,
            )
            logger.info("    %s", lead.url)

    # ── Persist output ──
    output = {
        "scan_timestamp": ts,
        "config": {"min_reward_usd": MIN_REWARD_USD, "min_ratio": MIN_RATIO},
        "summary": {
            "total": len(all_leads),
            "algora": len(algora_raw),
            "polar": len(polar_raw),
            "immunefi": len(immunefi_raw),
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
        "accepted": [asdict(l) for l in accepted],
        "rejected": [asdict(l) for l in rejected],
    }

    out_path = RESULTS_DIR / f"scan_{ts}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info("Results written → %s", out_path)

    # Persist to CORTEX Ledger
    await persist_to_ledger(accepted)

    logger.info("=" * 60)
    logger.info("SCAN COMPLETE — next run in 6h (launchd)")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_scan())
