#!/bin/bash
# Sovereign Pre-commit hook v1.0 - Anti-Entropy Protocol

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" || true)

if [ -n "$STAGED_FILES" ]; then
    echo "⚡ [SOVEREIGN] Purging entropy with Ruff..."
    
    # Run formatting and checks
    ruff format $STAGED_FILES
    ruff check --fix $STAGED_FILES
    
    # Re-stage modified files
    git add $STAGED_FILES
fi

exit 0
