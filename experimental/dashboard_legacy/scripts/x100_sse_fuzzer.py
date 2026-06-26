#!/usr/bin/env python3
"""
∴ OUROBOROS-X100-SSE-FUZZER v1.0
Real-time SSE streaming membrane for target repo fuzzing.

Pipeline:
  1. JIT assimilatee (git assimilate --depth 1) → /tmp/cortex_x100_fuzz/<repo>
  2. AST Regex Scan — Walk .sol files, extract contracts + public functions
  3. VSA keyword tensor matching → exergy score per contract
  4. Strike dispatch for high-exergy contracts (≥ 5.0)
  5. SSE yield — each step emits structured JSON event

∴ Axioms: Ω₂ (Thermodynamic), Ω₆ (Execution), Ω₉ (Truth)
∴ Reality: C5-REAL — All operations are real git assimilates and real AST scans.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import urlparse

# ── VSA Keyword Tensor (mirrors strike.rs) ────────────────────
VULN_KEYWORDS = [
    "reentrancy", "reentrant", "flash", "overflow", "underflow",
    "delegatecall", "selfdestruct", "access", "oracle", "frontrun",
    "sandwich", "sload", "extcodesize", "tx.origin", "block.timestamp",
    "unchecked", "transfer", "call.value", "low-level", "assembly",
    "suicide", "callcode", "staticcall", "create2", "msg.value",
]

FUZZ_DIR = Path("/tmp/cortex_x100_fuzz")

# ── ANSI Industrial Noir ─────────────────────────────────────
C = {
    "B": "\033[38;2;43;59;229m",
    "G": "\033[38;2;0;255;136m",
    "R": "\033[38;2;255;59;48m",
    "D": "\033[38;2;90;90;90m",
    "V": "\033[38;2;102;0;255m",
    "W": "\033[97m",
    "X": "\033[0m",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event line."""
    payload = {"type": event_type, "timestamp": _now_iso(), "data": data}
    return json.dumps(payload)


def _parse_repo_name(target_url: str) -> str:
    """Extract owner/repo from GitHub URL."""
    parsed = urlparse(target_url)
    path = parsed.path.strip("/")
    # Remove .git suffix
    if path.endswith(".git"):
        path = path[:-4]
    return path


def _assimilate_repo(target_url: str) -> tuple[Path | None, str]:
    """JIT shallow assimilate. Returns (assimilate_path, error_or_empty)."""
    repo_name = _parse_repo_name(target_url)
    safe_name = repo_name.replace("/", "_")
    assimilate_path = FUZZ_DIR / safe_name

    # Reuse if recent (< 1 hour)
    if assimilate_path.exists():
        age_seconds = time.time() - assimilate_path.stat().st_mtime
        if age_seconds < 3600:
            return assimilate_path, ""
        shutil.rmtree(assimilate_path, ignore_errors=True)

    FUZZ_DIR.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "assimilate", "--depth", "1", "--single-branch", target_url, str(assimilate_path)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()[:500]
        return assimilate_path, ""
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT: git assimilate exceeded 120s"
    except Exception as e:
        return None, str(e)


# ── AST Regex Scanner ────────────────────────────────────────

# Patterns for Solidity
RE_CONTRACT = re.compile(
    r"(?:contract|library|interface)\s+(\w+)", re.MULTILINE
)
RE_FUNCTION = re.compile(
    r"function\s+(\w+)\s*\([^)]*\)\s*(?:external|public)", re.MULTILINE
)


def _scan_sol_file(filepath: Path) -> list[dict]:
    """Scan a single .sol file. Returns list of findings."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    findings = []
    contracts = RE_CONTRACT.findall(content)
    functions = RE_FUNCTION.findall(content)
    content_lower = content.lower()

    # VSA keyword tensor collapse
    keyword_hits = []
    for kw in VULN_KEYWORDS:
        if kw in content_lower:
            keyword_hits.append(kw)

    hit_count = len(keyword_hits)
    # Exergy: base 1.0 + 0.8 per keyword hit + 0.3 per exposed function
    exergy = round(1.0 + (hit_count * 0.8) + (len(functions) * 0.3), 2)

    if contracts:
        findings.append({
            "file": str(filepath),
            "contracts": contracts,
            "functions": functions[:20],
            "keyword_hits": keyword_hits,
            "hit_count": hit_count,
            "exergy": exergy,
            "lines": content.count("\n") + 1,
        })

    return findings


def _scan_directory(assimilate_path: Path) -> list[dict]:
    """Walk all .sol files in assimilated repo."""
    all_findings = []
    sol_files = list(assimilate_path.rglob("*.sol"))

    for sol_file in sol_files:
        # Skip node_modules, lib, forge-std
        relative = str(sol_file.relative_to(assimilate_path))
        if any(skip in relative for skip in ["node_modules", "forge-std", ".git"]):
            continue
        findings = _scan_sol_file(sol_file)
        all_findings.extend(findings)

    # Sort by exergy descending
    all_findings.sort(key=lambda f: f["exergy"], reverse=True)
    return all_findings


# ── Strike Dispatch ──────────────────────────────────────────

def _dispatch_to_strike(finding: dict, target_url: str) -> dict:
    """Dispatch high-exergy finding through the native Rust strike gate."""
    try:
        from strike_engine import execute_strike
        title = f"{finding['contracts'][0]} ({finding['hit_count']} VSA hits)"
        execute_strike(
            source_name="x100-sse-fuzzer",
            title=title,
            html_url=target_url,
            exergy=finding["exergy"],
        )
        return {"status": "DISPATCHED", "target": title}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def _persist_finding(finding: dict, target_url: str) -> dict:
    """Persist finding to the native ledger."""
    try:
        from db import upsert_bounty
        import hashlib
        bounty_id = int(hashlib.sha256(
            f"{target_url}_{finding['contracts'][0]}".encode()
        ).hexdigest()[:8], 16)

        upsert_bounty(
            source="x100-sse-fuzzer",
            bounty_id=bounty_id,
            title=f"{finding['contracts'][0]} — {finding['hit_count']} vuln keywords",
            url=target_url,
            author="cortex-x100",
            exergy=finding["exergy"],
        )
        return {"status": "PERSISTED", "bounty_id": bounty_id}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ── Main SSE Generator ──────────────────────────────────────

async def x100_fuzz_generator(target_url: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events for each stage of the fuzzing pipeline.
    Designed to be consumed by EventSourceResponse.
    """
    t0 = time.monotonic()
    repo_name = _parse_repo_name(target_url)

    # ── Phase 1: assimilatee ────────────────────────────────────────
    yield _sse_event("scan", {
        "phase": "assimilate",
        "message": f"JIT assimilating {repo_name}...",
        "target_url": target_url,
    })

    assimilate_path, assimilate_error = _assimilate_repo(target_url)

    if assimilate_path is None:
        yield _sse_event("error", {
            "phase": "assimilate",
            "message": f"assimilatee failed: {assimilate_error}",
        })
        return

    yield _sse_event("scan", {
        "phase": "assimilate_complete",
        "message": f"assimilated to {assimilate_path}",
        "duration_ms": round((time.monotonic() - t0) * 1000),
    })

    # ── Phase 2: AST Scan ─────────────────────────────────────
    yield _sse_event("scan", {
        "phase": "ast_scan",
        "message": "Walking .sol files — AST regex tensor collapse...",
    })

    t_scan = time.monotonic()
    findings = _scan_directory(assimilate_path)
    scan_duration = round((time.monotonic() - t_scan) * 1000)

    sol_count = len(list(assimilate_path.rglob("*.sol")))
    yield _sse_event("scan", {
        "phase": "ast_complete",
        "message": f"Scanned {sol_count} .sol files",
        "total_findings": len(findings),
        "duration_ms": scan_duration,
    })

    if not findings:
        yield _sse_event("complete", {
            "message": "No Solidity contracts found in target.",
            "total_duration_ms": round((time.monotonic() - t0) * 1000),
        })
        return

    # ── Phase 3: Emit Findings ────────────────────────────────
    strikes_dispatched = 0
    persisted_count = 0

    for i, finding in enumerate(findings):
        relative_file = finding["file"]
        if str(assimilate_path) in relative_file:
            relative_file = relative_file.replace(str(assimilate_path) + "/", "")

        yield _sse_event("finding", {
            "index": i + 1,
            "total": len(findings),
            "file": relative_file,
            "contracts": finding["contracts"],
            "functions": finding["functions"][:10],
            "keyword_hits": finding["keyword_hits"],
            "exergy": finding["exergy"],
            "lines": finding["lines"],
        })

        # Persist all findings with exergy >= 2.0
        if finding["exergy"] >= 2.0:
            persist_result = _persist_finding(finding, target_url)
            if persist_result["status"] == "PERSISTED":
                persisted_count += 1

        # ── Phase 4: Strike Dispatch (exergy >= 5.0) ──────────
        if finding["exergy"] >= 5.0:
            yield _sse_event("strike", {
                "message": f"HIGH EXERGY ({finding['exergy']}) — Dispatching strike on {finding['contracts'][0]}",
                "contract": finding["contracts"][0],
                "exergy": finding["exergy"],
            })

            strike_result = _dispatch_to_strike(finding, target_url)
            strikes_dispatched += 1

            yield _sse_event("strike", {
                "message": f"Strike result: {strike_result['status']}",
                "result": strike_result,
            })

    # ── Phase 5: Summary ──────────────────────────────────────
    total_duration = round((time.monotonic() - t0) * 1000)
    max_exergy = max(f["exergy"] for f in findings) if findings else 0

    yield _sse_event("complete", {
        "repo": repo_name,
        "sol_files_scanned": sol_count,
        "total_findings": len(findings),
        "persisted": persisted_count,
        "strikes_dispatched": strikes_dispatched,
        "max_exergy": max_exergy,
        "total_duration_ms": total_duration,
    })


# ── CLI Mode (for direct terminal execution) ─────────────────

def run_cli(target_url: str):
    """Synchronous CLI mode — prints events to terminal."""
    import asyncio

    async def _run():
        print(f"\n{C['B']}╔══════════════════════════════════════════════════╗{C['X']}")
        print(f"{C['B']}║{C['W']}  ∴ OUROBOROS-X100-SSE-FUZZER v1.0                 {C['B']}║{C['X']}")
        print(f"{C['B']}╚══════════════════════════════════════════════════╝{C['X']}")
        print(f"  {C['D']}Target:{C['X']} {target_url}")
        print(f"  {C['D']}Reality:{C['X']} C5-REAL (All operations are real)\n")

        async for event_str in x100_fuzz_generator(target_url):
            event = json.loads(event_str)
            t = event["type"]
            d = event["data"]

            if t == "scan":
                icon = f"{C['B']}◈{C['X']}"
                print(f"  {icon} {C['D']}[{d.get('phase', 'scan')}]{C['X']} {d['message']}")
            elif t == "finding":
                exergy = d["exergy"]
                color = C["G"] if exergy >= 5.0 else C["D"] if exergy < 2.0 else C["W"]
                hits = ", ".join(d["keyword_hits"][:5]) if d["keyword_hits"] else "none"
                print(
                    f"  {color}[{d['index']}/{d['total']}]{C['X']} "
                    f"{C['W']}{', '.join(d['contracts'])}{C['X']} "
                    f"{C['D']}exergy:{C['X']}{exergy:.1f} "
                    f"{C['D']}hits:{C['X']}{hits} "
                    f"{C['D']}{d['lines']}L{C['X']}"
                )
            elif t == "strike":
                print(f"  {C['G']}⚡ [STRIKE]{C['X']} {d['message']}")
            elif t == "error":
                print(f"  {C['R']}✗ [ERROR]{C['X']} {d['message']}")
            elif t == "complete":
                print(f"\n{C['B']}{'─' * 50}{C['X']}")
                print(f"  {C['W']}Repo:{C['X']}          {d.get('repo', 'N/A')}")
                print(f"  {C['W']}.sol scanned:{C['X']}  {d.get('sol_files_scanned', 0)}")
                print(f"  {C['W']}Findings:{C['X']}      {d.get('total_findings', 0)}")
                print(f"  {C['G']}Persisted:{C['X']}     {d.get('persisted', 0)}")
                print(f"  {C['G']}Strikes:{C['X']}       {d.get('strikes_dispatched', 0)}")
                print(f"  {C['W']}Max Exergy:{C['X']}    {d.get('max_exergy', 0):.1f}")
                print(f"  {C['B']}Duration:{C['X']}      {d.get('total_duration_ms', 0)}ms")
                print(f"{C['B']}{'─' * 50}{C['X']}\n")

    asyncio.run(_run())


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 x100_sse_fuzzer.py <github_repo_url>")
        print("Example: python3 x100_sse_fuzzer.py https://github.com/OpenZeppelin/openzeppelin-contracts")
        sys.exit(1)

    # Init DB before running
    try:
        from db import init_db
        init_db()
    except Exception:
        pass

    run_cli(sys.argv[1])
