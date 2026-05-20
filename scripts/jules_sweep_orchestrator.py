#!/usr/bin/env python3
"""
jules_sweep_orchestrator.py
───────────────────────────
C5-REAL autonomous sweep coordinator for naroagutierrezgil.com.

Dispatches three parallel Jules task classes:
  • SEO      — meta tags, canonical, Open Graph, structured data, sitemap
  • A11Y     — skip-links, ARIA, alt text, color contrast, keyboard nav
  • IMAGES   — srcset, WebP, lazy-load, responsive breakpoints, CLS

Output appended to: cortex_audit_ledger.jsonl
Jules API:         https://jules.google.com/api/v1alpha  (env: JULES_API_KEY)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

# ── Constants ────────────────────────────────────────────────────────────────

TARGET_DOMAIN = "https://naroagutierrezgil.com"
JULES_BASE_URL = "https://aida.googleapis.com/v1/swebot"
LEDGER_PATH = Path(__file__).parent.parent / "cortex_audit_ledger.jsonl"
POLL_INTERVAL_S = 8
MAX_POLL_ROUNDS = 90  # 12 min max per task


# ── Data model ───────────────────────────────────────────────────────────────


class SweepKind(str, Enum):
    SEO = "seo"
    A11Y = "a11y"
    IMAGES = "images"


@dataclass
class SweepTask:
    kind: SweepKind
    target_url: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    jules_id: str | None = None
    status: str = "pending"
    findings: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: _now())
    completed_at: str | None = None


@dataclass
class SweepRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    domain: str = TARGET_DOMAIN
    tasks: list[SweepTask] = field(default_factory=list)
    started: str = field(default_factory=lambda: _now())
    finished: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Jules prompts per sweep kind ──────────────────────────────────────────────

SEO_PROMPT = """\
Perform a comprehensive SEO audit on {url}.

Check and report on:
1. Title tag — present, unique, 50-60 chars, keyword-rich
2. Meta description — present, 150-160 chars, compelling CTA
3. Canonical URL — correct self-referential canonical
4. Open Graph tags — og:title, og:description, og:image, og:url
5. Twitter Card meta tags
6. Structured data (JSON-LD) — Person, ArtGallery, or CreativeWork schema for Naroa Gutiérrez Gil
7. Sitemap.xml — exists and is valid
8. Robots.txt — permissive for main content
9. Heading hierarchy — single H1, logical H2-H6 nesting
10. Internal link structure — no orphaned pages

For each issue found, output:
  severity: critical | high | medium | low
  element: <what element>
  current: <current value or 'missing'>
  recommended: <what it should be>
  fix: <exact change needed>

Return as JSON array of findings.
""".strip()

A11Y_PROMPT = """\
Perform a WCAG 2.1 AA accessibility audit on {url}.

Check and report on:
1. Skip-navigation link — present and functional before main content
2. All images — non-decorative images have meaningful alt text
3. Interactive elements — all buttons and links have accessible names
4. ARIA landmarks — main, nav, header, footer regions declared
5. Color contrast — text meets 4.5:1 ratio (3:1 for large text)
6. Keyboard navigation — all interactive elements reachable via Tab
7. Focus indicators — visible focus rings on all interactive elements
8. Form labels — all inputs have associated <label> elements
9. Language attribute — <html lang="es"> set correctly
10. Heading structure — logical, non-skipping heading levels

For each issue, output:
  wcag_criterion: e.g. "1.1.1 Non-text Content"
  severity: critical | high | medium | low
  element: <CSS selector or description>
  issue: <description of the problem>
  fix: <recommended remediation>

Return as JSON array of findings.
""".strip()

IMAGES_PROMPT = """\
Perform a responsive images and Core Web Vitals audit on {url}.

Check and report on:
1. LCP image — has fetchpriority="high" and preload link
2. All <img> tags — have width and height attributes (CLS prevention)
3. srcset and sizes — modern responsive images with at least 2 breakpoints
4. WebP/AVIF — images served in next-gen formats with fallback
5. Lazy loading — below-fold images use loading="lazy"
6. Image dimensions — no images scaled down >50% in CSS (oversized source)
7. Total image payload — page images under 500KB cumulative
8. Artwork grid images in /naroagutierrez — verify procedural SVGs render correctly

For each issue, output:
  metric_impact: LCP | CLS | TBT | none
  severity: critical | high | medium | low
  element: <img src or selector>
  issue: <description>
  fix: <recommended change>

Return as JSON array of findings.
""".strip()

PROMPTS: dict[SweepKind, str] = {
    SweepKind.SEO: SEO_PROMPT,
    SweepKind.A11Y: A11Y_PROMPT,
    SweepKind.IMAGES: IMAGES_PROMPT,
}


def get_keychain_token() -> str | None:
    try:
        import subprocess
        import base64
        import json

        out = subprocess.check_output(
            ["security", "find-generic-password", "-s", "jules-cli", "-a", "default", "-w"],
            text=True,
        ).strip()
        if out.startswith("go-keyring-base64:"):
            b64_part = out.split("go-keyring-base64:")[1]
            decoded = base64.b64decode(b64_part)
            token_data = json.loads(decoded.decode("utf-8"))
            return token_data.get("access_token")
    except Exception:
        pass
    return None


def get_git_source_id() -> str:
    try:
        import subprocess

        url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], text=True
        ).strip()
        if url.endswith(".git"):
            url = url[:-4]
        if "github.com:" in url:
            parts = url.split("github.com:")[-1]
        elif "github.com/" in url:
            parts = url.split("github.com/")[-1]
        else:
            parts = url.split("/")[-2:]
            parts = "/".join(parts)
        return f"github/{parts}"
    except Exception:
        return "github/borjamoskv/Cortex-Persist"


# ── Jules API client ──────────────────────────────────────────────────────────


class JulesClient:
    """Thin async wrapper around the Jules (swebot) REST API."""

    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def create_task(
        self, title: str, prompt: str, source_id: str, client: httpx.AsyncClient
    ) -> str:
        """Submit a task and return its Jules task ID."""
        resp = await client.post(
            f"{JULES_BASE_URL}/tasks",
            headers=self._headers,
            json={
                "title": title,
                "description": prompt,
                "sourceId": source_id,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["taskId"]

    async def poll_task(
        self,
        task_id: str,
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """Poll until done/failed. Returns the completed task object."""
        for _ in range(MAX_POLL_ROUNDS):
            resp = await client.get(
                f"{JULES_BASE_URL}/tasks/{task_id}",
                headers=self._headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            task = data.get("task", {})
            status = task.get("swebotTaskStatus", "")
            if status in (
                "SWEBOT_TASK_STATUS_COMPLETED",
                "SWEBOT_TASK_STATUS_FAILED",
                "SWEBOT_TASK_STATUS_CANCELLED",
            ):
                return task
            if task.get("isAwaitingReview") is True:
                return task
            await asyncio.sleep(POLL_INTERVAL_S)
        raise TimeoutError(f"Jules task {task_id} did not complete in time")


# ── Sweep execution ───────────────────────────────────────────────────────────


async def run_sweep(task: SweepTask, jules: JulesClient) -> SweepTask:
    """Dispatch one sweep task to Jules, poll, parse findings."""
    source_id = get_git_source_id()
    title = f"Audit {TARGET_DOMAIN} ({task.kind.value})"
    prompt = PROMPTS[task.kind].format(url=task.target_url)
    print(f"  [{task.kind.upper()}] Dispatching → Jules...", flush=True)

    async with httpx.AsyncClient() as client:
        try:
            jules_id = await jules.create_task(title, prompt, source_id, client)
            task.jules_id = jules_id
            task.status = "dispatched"
            print(f"  [{task.kind.upper()}] Jules ID: {jules_id}", flush=True)

            result = await jules.poll_task(jules_id, client)
            task.completed_at = _now()

            status = result.get("swebotTaskStatus", "")
            is_awaiting = result.get("isAwaitingReview", False)

            if status == "SWEBOT_TASK_STATUS_COMPLETED" or is_awaiting:
                task.status = "completed"
                # Extract findings
                findings = []
                found_json_file = False
                activity_steps = result.get("activitySteps", [])
                for step in activity_steps:
                    act = step.get("agentActivity", {})
                    if "taskCompleted" in act:
                        tc = act["taskCompleted"]
                        commit = tc.get("commit", {})
                        patch = commit.get("patch", {})
                        diffs = patch.get("fileDiffsV2", []) or patch.get("fileDiffs", [])
                        for d in diffs:
                            path = d.get("fileAfter", {}).get("path", "")
                            if path.endswith(".json"):
                                b64_content = d.get("fileAfter", {}).get("contentAsBytes", "")
                                if b64_content:
                                    import base64

                                    try:
                                        content_str = base64.b64decode(b64_content).decode("utf-8")
                                        parsed = json.loads(content_str)
                                        if isinstance(parsed, dict):
                                            found_list = False
                                            for _k, v in parsed.items():
                                                if isinstance(v, list):
                                                    findings.extend(v)
                                                    found_list = True
                                                    break
                                            if not found_list:
                                                findings.append(parsed)
                                        elif isinstance(parsed, list):
                                            findings.extend(parsed)
                                        found_json_file = True
                                    except Exception as e:
                                        print(f"Failed to decode/parse json file {path}: {e}")

                if not found_json_file:
                    text_parts = []
                    for step in activity_steps:
                        act = step.get("agentActivity", {})
                        if "agentMessaged" in act:
                            text_parts.append(act["agentMessaged"].get("text", ""))
                        elif "codeReviewRequested" in act:
                            text_parts.append(act["codeReviewRequested"].get("criticOutput", ""))

                    full_text = "\n\n".join(text_parts)
                    import re

                    json_blocks = re.findall(r"```json\s*(.*?)\s*```", full_text, re.DOTALL)
                    for jb in json_blocks:
                        try:
                            parsed = json.loads(jb)
                            if isinstance(parsed, list):
                                findings.extend(parsed)
                            elif isinstance(parsed, dict):
                                for _k, v in parsed.items():
                                    if isinstance(v, list):
                                        findings.extend(v)
                                        break
                                else:
                                    findings.append(parsed)
                            found_json_file = True
                        except Exception:
                            pass

                    if not findings:
                        findings.append({"raw_output": full_text or "No text output found."})

                task.findings = findings
            else:
                task.status = "failed"
                task.findings = [{"error": result.get("error", "unknown")}]

        except httpx.HTTPStatusError as exc:
            task.status = "api_error"
            task.findings = [
                {"http_status": exc.response.status_code, "detail": str(exc.response.text)}
            ]
        except TimeoutError as exc:
            task.status = "timeout"
            task.findings = [{"error": str(exc)}]
        except Exception as exc:  # noqa: BLE001
            task.status = "error"
            task.findings = [{"error": str(exc)}]

    _print_findings(task)
    return task


def _print_findings(task: SweepTask) -> None:
    """Print a compact summary of findings to stdout."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in task.findings:
        sev = f.get("severity", "").lower()
        if sev in counts:
            counts[sev] += 1

    total = len(task.findings)
    summary = " · ".join(f"{v} {k}" for k, v in counts.items() if v > 0) or "no structured findings"

    icon = "✅" if task.status == "completed" else "❌"
    print(
        f"  {icon} [{task.kind.upper()}] {total} findings — {summary}",
        flush=True,
    )


# ── Ledger persistence ────────────────────────────────────────────────────────


def append_to_ledger(run: SweepRun) -> None:
    """Append the full run record to cortex_audit_ledger.jsonl."""
    record = {
        "event": "jules_sweep_run",
        "run_id": run.run_id,
        "domain": run.domain,
        "started": run.started,
        "finished": run.finished,
        "tasks": [asdict(t) for t in run.tasks],
    }
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\n📒 Ledger updated → {LEDGER_PATH.name}", flush=True)


# ── CLI summary report ────────────────────────────────────────────────────────


def print_report(run: SweepRun) -> None:
    total_findings = sum(len(t.findings) for t in run.tasks)
    critical = sum(1 for t in run.tasks for f in t.findings if f.get("severity") == "critical")
    print("\n" + "═" * 60)
    print(f"  JULES SWEEP REPORT — {run.domain}")
    print(f"  Run ID : {run.run_id}")
    print(f"  Started: {run.started}")
    print("─" * 60)
    for t in run.tasks:
        icon = "✅" if t.status == "completed" else "❌"
        print(f"  {icon}  {t.kind.upper():8s}  {len(t.findings):3d} findings  [{t.status}]")
    print("─" * 60)
    print(f"  Total findings : {total_findings}")
    print(f"  Critical       : {critical}")
    print("═" * 60 + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────


async def main() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, val = stripped.split("=", 1)
                    os.environ[key] = val

    api_key = os.getenv("JULES_API_KEY", "")
    if not api_key:
        api_key = get_keychain_token() or ""

    if not api_key:
        print(
            "⚠️  JULES_API_KEY not set and could not retrieve credentials from Keychain — running in DRY-RUN mode (no real API calls).",
            file=sys.stderr,
        )
        _dry_run()
        return

    jules = JulesClient(api_key)

    run = SweepRun()
    run.tasks = [
        SweepTask(kind=SweepKind.SEO, target_url=TARGET_DOMAIN),
        SweepTask(kind=SweepKind.A11Y, target_url=TARGET_DOMAIN),
        SweepTask(kind=SweepKind.IMAGES, target_url=TARGET_DOMAIN),
    ]

    print(f"\n🚀 Jules Sweep — {TARGET_DOMAIN}")
    print(f"   Run ID: {run.run_id}\n")

    # Dispatch all three sweeps concurrently
    completed = await asyncio.gather(
        *[run_sweep(task, jules) for task in run.tasks],
        return_exceptions=False,
    )
    run.tasks = list(completed)
    run.finished = _now()

    print_report(run)
    append_to_ledger(run)


def _dry_run() -> None:
    """Emit stub ledger record with C4-SIMULATION declaration."""
    run = SweepRun()
    run.finished = _now()
    run.tasks = [
        SweepTask(
            kind=k,
            target_url=TARGET_DOMAIN,
            status="dry_run",
            findings=[
                {
                    "severity": "info",
                    "element": "DRY-RUN",
                    "issue": "C4-SIMULATION — no real Jules API call made",
                    "fix": "Set JULES_API_KEY env var for C5-REAL execution",
                }
            ],
        )
        for k in SweepKind
    ]
    run.finished = _now()
    print_report(run)
    append_to_ledger(run)
    print("  Declared: C4-SIMULATION — no real API calls executed.\n")


if __name__ == "__main__":
    asyncio.run(main())
