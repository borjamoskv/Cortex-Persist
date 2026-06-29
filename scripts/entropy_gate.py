#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: entropy-gate
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _changed_files import changed_files

try:
    from radon.complexity import cc_visit
except ImportError:
    print("❌ Entropy Gate requires 'radon'. Install it in your environment: pip install radon")
    sys.exit(1)

# Sovereign Complexity Limit (Axiom 14)
CC_THRESHOLD = 15


def _resolve_python_paths(files: list[str]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for filename in files:
        path = Path.cwd() / filename
        if path.suffix != ".py" or not path.exists() or path in seen:
            continue
        seen.add(path)
        resolved.append(path)
    return resolved


def get_candidate_python_files() -> tuple[list[Path], str]:
    """Resolve Python files from staged changes, or from the local diff if index is empty."""
    candidates, source = changed_files(include_untracked=True, prefer_staged=True)
    return _resolve_python_paths([str(path) for path in candidates]), source


def analyze_file(filepath: Path) -> bool:
    """Evaluates the file's entropy and returns False if it fails the threshold."""
    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()

        blocks = cc_visit(code)
        if not blocks:
            return True

        # Find the most complex block (function or class)
        worst_block = max(blocks, key=lambda b: b.complexity)
        max_cc = worst_block.complexity

        if max_cc > CC_THRESHOLD:
            print(f"\n🛑 [ENTROPY GATE] {filepath.name} has too much static entropy.")
            print(f"   ► Element: '{worst_block.name}' at line {worst_block.lineno}")
            print(f"   ► Complexity: {max_cc} (Limit: {CC_THRESHOLD})")
            print("   ► Escort: You need to break up this logic. Extract helpers and use Guard Clauses.")
            print(f"   💊 Auto-Healing available: `cortex heal {filepath.name}`")
            return False

        return True
    except (OSError, SyntaxError, UnicodeDecodeError):
        # Silence parsing errors (pydantic/syntax errors will catch them later)
        return True


def main():
    candidate_files, source = get_candidate_python_files()
    if not candidate_files:
        sys.exit(0)  # Nothing to scan, continue with the commit

    if source == "staged":
        print(f"👁️  ENTROPY GATE | Evaluating static entropy in {len(candidate_files)} staged files...")
    else:
        print(
            f"👁️  ENTROPY GATE | No staged files; evaluating {len(candidate_files)} files from local diff..."
        )

    failed = False
    for f in candidate_files:
        if not analyze_file(f):
            failed = True

    if failed:
        print("\n❌ COMMIT REJECTED: Entropy exceeds Sovereign level (CC > 15).")
        print(
            "💡 [SOVEREIGN TIP] Refactor with /mejoralo-v9.1 before retrying the commit."
        )
        sys.exit(1)

    print("✅ Clean code. Landauer's Principle respected.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
