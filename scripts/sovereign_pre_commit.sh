#!/bin/bash
# [C5-REAL] Exergy-Maximized
# Sovereign Pre-commit hook v1.0 - Anti-Entropy Protocol

set -euo pipefail

collect_python_files() {
    local -n target_ref=$1
    local -n staged_mode_ref=$2
    local -A seen=()
    local path=""
    local staged_files=()
    local unstaged_files=()
    local untracked_files=()

    mapfile -t staged_files < <(git diff --cached --name-only --diff-filter=ACMR -- '*.py')
    if [ ${#staged_files[@]} -gt 0 ]; then
        target_ref=("${staged_files[@]}")
        staged_mode_ref=1
        return
    fi

    mapfile -t unstaged_files < <(git diff --name-only --diff-filter=ACMR -- '*.py')
    mapfile -t untracked_files < <(git ls-files --others --exclude-standard -- '*.py')

    target_ref=()
    for path in "${unstaged_files[@]}" "${untracked_files[@]}"; do
        if [ -z "$path" ] || [ -n "${seen[$path]+x}" ]; then
            continue
        fi
        seen[$path]=1
        target_ref+=("$path")
    done
    staged_mode_ref=0
}

PYTHON_FILES=()
USING_STAGED=0
collect_python_files PYTHON_FILES USING_STAGED

if [ ${#PYTHON_FILES[@]} -gt 0 ]; then
    echo "⚡ [SOVEREIGN] Purging entropy with Ruff..."

    ruff format "${PYTHON_FILES[@]}"
    ruff check --fix "${PYTHON_FILES[@]}"

    if [ "$USING_STAGED" -eq 1 ]; then
        git add -- "${PYTHON_FILES[@]}"
    fi
fi

# ── Update Article Signatures ─────────────────────────────────
echo "⚡ [SOVEREIGN] Updating article signatures..."
python3 scripts/update_signatures.py

if [ "$USING_STAGED" -eq 1 ]; then
    git add src/pages/blog/*.astro 2>/dev/null || true
fi

exit 0
