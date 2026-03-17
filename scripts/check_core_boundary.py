"""
Core boundary guard.

Fails with exit code 1 if any forbidden satellite directory is found at the
repo root. Run locally or in CI to prevent recontamination.

Usage:
    python scripts/check_core_boundary.py
"""

from __future__ import annotations

from pathlib import Path

# Directories that must NOT exist at repo root.
# These are UX surfaces, marketing assets, demo apps, and experiments that
# live outside the trust-layer boundary by design.
FORBIDDEN: set[str] = {
    # Marketing / web surfaces
    "cortexpersist-landing",
    "cortexpersist-com",
    "cortexpersist-org",
    "cortexpersist-dev",
    "cortexpersist-docs",
    "cortexpersist-api",
    "web",
    "web-org",
    "sales-assets",
    "marketing",
    # Demo / app shells
    "lyria_app",
    "CortexDash.app",
    "dashboard",
    "experimental_ui",
    "awwwards-engine",
    # Experiments / personal
    "AgentArena",
    "experimental",
    "notebooks",
    "aether_drop",
    "auramem",
    "ShadowStudio",
    "sovereign-agency",
    # Audio / media projects
    "Rework_POC_Generations",
    "White_Pony_Master",
    "White_Pony_Stems",
    "Sources",
    # Distribution / airdrop
    "airdrops",
    "notebooklm_domains",
    "trompetas-inaki",
}

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    violations: list[str] = []
    for name in FORBIDDEN:
        if (ROOT / name).exists():
            violations.append(name)

    if violations:
        print("❌  Core boundary violated. Forbidden directories still present:")
        for item in sorted(violations):
            print(f"   - {item}")
        print()
        print("Resolve: git rm -r --cached <dir> && git commit -m 'refactor(core): purge <dir>'")
        return 1

    print("✅  Core boundary OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
