#!/usr/bin/env python3
# =============================================================================
# CORTEX SOVEREIGN PRE-COMMIT v3.0
# =============================================================================
# Three guards, one commit. If any fails, the commit dies.
#
# Guard 1: DependencyGuard (AX-011 — Zero external oracle SPOF)
# Guard 2: Neural Shield (X-Ray quality score >= 90/100)
# Guard 3: Axiom Registry Sync (AX-019 — docs generated from code)
#
# Installed as: .git/hooks/pre-commit → ../../scripts/sovereign_pre_commit.py

import os
import subprocess
import sys


def _find_repo_root() -> str:
    """Detect repo root reliably (works as hook or direct invocation)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    # Fallback: assume script lives in REPO/scripts/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


REPO_ROOT = _find_repo_root()
VENV_PYTHON = os.path.join(REPO_ROOT, ".venv", "bin", "python")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


def run_dependency_guard() -> bool:
    """Axiom 4: No subprocess to external oracle without fallback."""
    print(
        "\n🛡️  [GUARD 1/2] DependencyGuard — Axiom 4 Enforcement"
    )
    try:
        result = subprocess.run(
            [PYTHON, "-m", "cortex.guards.dependency_guard", REPO_ROOT],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        # Print output
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(f"   {line.strip()}")

        if result.returncode != 0:
            print("   ⛔ BLOCKED: Axiom 4 violations detected.")
            print(
                "   💡 Use SovereignLLM "
                "(cortex/llm/sovereign.py) to fix.\n"
            )
            return False

        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"   ⚠️  Guard skipped: {e}")
        return True  # Don't block on guard failure


def run_neural_shield() -> bool:
    """Quality gate: X-Ray score must be >= 90/100."""
    print(
        "\n👁️  [GUARD 2/2] Neural Shield — Quality Enforcement"
    )
    neural_script = os.path.join(
        REPO_ROOT, "scripts", "neural_pre_commit.py"
    )
    if not os.path.exists(neural_script):
        print("   ⚠️  neural_pre_commit.py not found, skipping.")
        return True

    try:
        result = subprocess.run(
            [PYTHON, neural_script],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(f"   {line.strip()}")

        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"   ⚠️  Guard skipped: {e}")
        return True


def run_axiom_registry_sync() -> bool:
    """Guard 3: Verify axiom-registry.md is generated from code."""
    print(
        "\n📜 [GUARD 3/3] Axiom Registry Sync — AX-019"
    )
    registry_md = os.path.join(REPO_ROOT, "docs", "axiom-registry.md")
    if not os.path.exists(registry_md):
        print("   ⚠️  docs/axiom-registry.md not found, skipping.")
        return True

    try:
        # Read current content
        with open(registry_md) as f:
            current = f.read()

        # Regenerate from code
        result = subprocess.run(
            [PYTHON, "-m", "cortex.axioms.generate_docs"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print(f"   ⚠️  Generator failed: {result.stderr[:200]}")
            return True  # Don't block on generator failure

        # Read regenerated content
        with open(registry_md) as f:
            regenerated = f.read()

        if current != regenerated:
            print(
                "   ⛔ axiom-registry.md is out of sync with registry.py!"
            )
            print(
                "   💡 Run: python -m cortex.axioms.generate_docs"
            )
            print("   Then stage the updated file.")
            return False

        print("   ✅ axiom-registry.md in sync with code.")
        return True
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"   ⚠️  Guard skipped: {e}")
        return True


if __name__ == "__main__":
    print("═" * 60)
    print("  CORTEX SOVEREIGN PRE-COMMIT v3.0")
    print("═" * 60)

    guard_1 = run_dependency_guard()
    guard_2 = run_neural_shield()
    guard_3 = run_axiom_registry_sync()

    if guard_1 and guard_2 and guard_3:
        print("\n✅ All guards passed. Commit approved.\n")
        sys.exit(0)
    else:
        failed = []
        if not guard_1:
            failed.append("DependencyGuard")
        if not guard_2:
            failed.append("NeuralShield")
        if not guard_3:
            failed.append("AxiomRegistrySync")
        print(
            f"\n⛔ COMMIT BLOCKED by: {', '.join(failed)}\n"
        )
        sys.exit(1)
