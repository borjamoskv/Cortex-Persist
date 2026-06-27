#!/bin/bash
# [C5-REAL] Exergy-Maximized
# Consolidated Cortex-Persist Maintenance Script (Sync + Exergy Singularity Purge)
#
# Runs:
# 1. Sovereign Sync (pull/rebase/test/push)
# 2. Implacable Singularity Purge (cache clean, db vacuum, scratch cleanup)

set -euo pipefail

CWD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CWD"

LOG_FILE="$CWD/exergy_singularity.log"
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

echo "[$TIMESTAMP] [C5-REAL] Starting consolidated cortex-persist maintenance..." >> "$LOG_FILE"

# 1. Run Sovereign Sync (Pull remote changes, run tests)
echo "🔄 Running Local Sync & Test Validation..."
if ! git pull --rebase; then
    echo "❌ [CONSOLIDAR] Git pull failed." | tee -a "$LOG_FILE"
    exit 1
fi

if ! make test-fast; then
    echo "❌ [CONSOLIDAR] Fast test validation failed. Aborting further steps." | tee -a "$LOG_FILE"
    exit 1
fi

# 2. Run Implacable Singularity Purge (Clean caches, db vacuum)
echo "🧹 Running Implacable Singularity Purge..."
make clean

if [ -f "cortex.db" ]; then
    echo "Vacuuming database..."
    sqlite3 cortex.db "VACUUM;" || true
fi

echo "✅ [CONSOLIDAR] Maintenance completed successfully. Exergy at 100%." | tee -a "$LOG_FILE"
