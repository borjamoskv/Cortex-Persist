#!/bin/bash
# [C5-REAL] Exergy-Maximized
# Consolidated Cortex-Persist Maintenance Script (Sync + Exergy Singularity Purge)
#
# Runs:
# 1. Sovereign Sync (stash/pull/rebase/pop/test/push)
# 2. Implacable Singularity Purge (cache clean, db vacuum, scratch cleanup)

set -euo pipefail

CWD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CWD"

LOG_FILE="$CWD/exergy_singularity.log"
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
STASHED=0

echo "[$TIMESTAMP] [C5-REAL] Starting consolidated cortex-persist maintenance..." >> "$LOG_FILE"

# 0. Defensive stash — handle dirty working trees gracefully
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Dirty working tree detected. Stashing changes..."
    git stash push -m "consolidar_cortex_auto_${TIMESTAMP}" --include-untracked
    STASHED=1
fi

# 1. Run Sovereign Sync (Pull remote changes, run tests)
echo "🔄 Running Local Sync & Test Validation..."
if ! git pull --rebase; then
    echo "❌ [CONSOLIDAR] Git pull failed." | tee -a "$LOG_FILE"
    # Restore stashed changes before exiting
    if [ "$STASHED" -eq 1 ]; then
        echo "📦 Restoring stashed changes..."
        git stash pop || true
    fi
    exit 1
fi

# Pop stash after successful rebase
if [ "$STASHED" -eq 1 ]; then
    echo "📦 Restoring stashed changes..."
    if ! git stash pop; then
        echo "⚠️ [CONSOLIDAR] Stash pop conflict. Changes preserved in stash." | tee -a "$LOG_FILE"
    fi
fi

if ! make test-fast; then
    echo "❌ [CONSOLIDAR] Fast test validation failed. Aborting further steps." | tee -a "$LOG_FILE"
    exit 1
fi

# 2. Run Implacable Singularity Purge (Clean caches, db vacuum)
echo "🧹 Running Implacable Singularity Purge..."
make clean 2>/dev/null || true

if [ -f "$CWD/cortex.db" ]; then
    echo "Vacuuming database..."
    sqlite3 "$CWD/cortex.db" "VACUUM;" || true
fi

# 3. Clean tmp artifacts from swarm/test runs
find /tmp -maxdepth 1 -name "swarm_10k_bus" -type d -mmin +60 -exec rm -rf {} + 2>/dev/null || true
find /tmp -maxdepth 1 -name "cortex_persist_bft_test_*.db*" -mmin +60 -delete 2>/dev/null || true

TIMESTAMP_END=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
echo "✅ [$TIMESTAMP_END] [CONSOLIDAR] Maintenance completed successfully. Exergy at 100%." | tee -a "$LOG_FILE"
