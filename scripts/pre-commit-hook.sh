#!/bin/bash
# .git/hooks/pre-commit
# CORTEX Sovereign Hook - v6.0 (Cycle 7)

echo "─── CORTEX Sovereign Guard: TAINT CHECK ───"

# Run the TaintGuard script
python3 -m cortex.guards.taint

if [ $? -ne 0 ]; then
    echo "❌ Commit rejected: Causal Taint missing or invalid (Ω1)."
    exit 1
fi

echo "✅ Taint verification passed. Proceeding..."
exit 0
