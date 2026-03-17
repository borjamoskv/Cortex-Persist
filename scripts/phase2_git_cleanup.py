# Phase 2 — Git Operational Checklist
# Cortex-Persist Root Extraction & Satellite Separation

# This script DOES NOT modify any files directly.
# It prints the git rm commands needed to extract satellite folders
# from the working tree. Review, then paste into your shell.

# Usage:
#   python3 scripts/phase2_git_cleanup.py
#   python3 scripts/phase2_git_cleanup.py --dry-run   (default — just prints)
#   python3 scripts/phase2_git_cleanup.py --execute   (runs git rm -r)

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────
# SATELLITE FOLDERS — safe to git rm from core
# ─────────────────────────────────────────────
SATELLITE_DIRS = {
    # cortex-persist-site
    "cortexpersist-com": "cortex-persist-site",
    "cortexpersist-landing": "cortex-persist-site",
    "cortexpersist-dev": "cortex-persist-site",
    "cortexpersist-org": "cortex-persist-site",
    "cortexpersist-docs": "cortex-persist-site",
    "awwwards-engine": "cortex-persist-site",
    # cortex-persist-apps
    "cortexpersist-api": "cortex-persist-apps",
    "CortexDash.app": "cortex-persist-apps",
    "dashboard": "cortex-persist-apps",
    "sovereign-agency": "cortex-persist-apps",
    # cortex-labs
    "aether_drop": "cortex-labs",
    "airdrops": "cortex-labs",
    "auramem": "cortex-labs",
    "cortex_eguzkia": "cortex-labs",
    "cortex_iturria": "cortex-labs",
    "experimental_ui": "cortex-labs",
    "ShadowStudio": "cortex-labs",
    "White_Pony_Master": "cortex-labs",
    "White_Pony_Stems": "cortex-labs",
    "Rework_POC_Generations": "cortex-labs",
    "Sources": "cortex-labs",
}

# ─────────────────────────────────────────────
# NON-CORE ROOT FILES — remove from tracked tree
# (These are NOT code files useful for the package)
# ─────────────────────────────────────────────
NON_CORE_ROOT_FILES = [
    "SOVEREIGN_MANIFESTO.md",
    "COMMERCE_STARVATION_PIPELINE.md",
    "architecture_endgame.md",
    "nemesis.md",
    "manifest_blockchain_forensics.yaml",
    "cortex_notebooklm_digest.md",
    "cortex_notebooklm_guide.md",
    "create_docx.py",
    "analyze_entropy.py",
    "analyze_exceptions.py",
    "extract_pdf.py",
    "check_embeddings.py",
    "store_arxiv.py",
    "ingest_handbook.py",
    "run_autodidact.py",
    "run_autodidact_batch_yt.py",
    "run_autodidact_fixed.py",
    "run_autodidact_microbiome.py",
    "run_mejoralo_10.py",
    "run_mejoralo_50.py",
    "run_mejoralo_100.py",
    "demo_entropia.py",
    "daemon_orchestrator.py",
    "cortex_load.py",
    "test_breaker.py",
    "test_decrypt.py",
    "test_epoch8.py",
    "test_ghost.py",
    "test_mcp.py",
    "test_search.py",
    "tracer.py",
    "bad_animation.html",
    "cortex_audit_report.md",
    "cortex_blacklist_master.json",
    "AUDITORIA_SEGURIDAD_GITHUB.md",
    "implementation_plan.md",
    # DB files — must only ever exist in .gitignore
    "cortex.db",
]

# ─────────────────────────────────────────────
# ITEMS REQUIRING A DECISION FIRST (not auto-removed)
# ─────────────────────────────────────────────
DECISION_REQUIRED = {
    "cortex-sdk": "Merge into sdk/python/ or create standalone cortex-persist-sdk repo",
    "cortex-hypervisor": "Merge scheduling logic into cortex/daemon/ or move to cortex-labs",
}


def run(cmd: list[str], dry_run: bool) -> None:
    print("  " + " ".join(cmd))
    if not dry_run:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [WARN] exit {result.returncode}: {result.stderr.strip()}")


def main(dry_run: bool = True) -> None:
    mode = "DRY-RUN (no files touched)" if dry_run else "⚡ LIVE — MODIFYING GIT TREE"
    print(f"\n{'='*60}")
    print(f"  Phase 2 Git Extraction Checklist — {mode}")
    print(f"{'='*60}\n")

    print("── Satellite directories ──────────────────────────────────")
    by_target: dict[str, list[str]] = {}
    for path, target in SATELLITE_DIRS.items():
        by_target.setdefault(target, []).append(path)

    for target, paths in sorted(by_target.items()):
        print(f"\n  → Future repo: github.com/borjamoskv/{target}")
        for p in paths:
            full = ROOT / p
            if full.exists():
                run(["git", "rm", "-r", "--cached", p], dry_run)
                print(f"       echo '{p}' >> .gitignore")
            else:
                print(f"  [SKIP] {p} — already absent")

    print("\n── Non-core root files ────────────────────────────────────")
    for f in NON_CORE_ROOT_FILES:
        full = ROOT / f
        if full.exists():
            run(["git", "rm", "--cached", f], dry_run)
        else:
            print(f"  [SKIP] {f} — already absent")

    print("\n── Decision required (not auto-removed) ───────────────────")
    for path, reason in DECISION_REQUIRED.items():
        print(f"  ⚠  {path}: {reason}")

    print(f"\n{'='*60}")
    print("  Next: commit with message 'chore(phase2): extract satellites'")
    print("  Then update .gitignore to prevent satellite re-entry.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 Git separation checklist.")
    parser.add_argument(
        "--execute", action="store_true", help="Actually run git rm commands (default: dry-run)"
    )
    args = parser.parse_args()
    main(dry_run=not args.execute)
