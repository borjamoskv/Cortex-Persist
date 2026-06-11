#!/bin/bash
set -euo pipefail
# MULTIPLIER: x10 (Centuria Deep Purge)
# TARGET: Ultimate Entropy Annihilation

echo "[C5-REAL] Initiating Exergy x10 Deep Purge..."

cd /Users/borjafernandezangulo/10_PROJECTS/cortex-persist

# 1. Python Dead Weight Annihilation
echo "[1/4] Purging PyCache & Test Entropy..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# 2. Rust Cargo Anergy Annihilation
echo "[2/4] Purging Rust Build Artifacts..."
if [ -d "cortex_rs" ]; then
    cd cortex_rs && cargo clean && cd ..
fi

# 3. Node/NPM Entropy Annihilation
echo "[3/4] Purging NPM Cache..."
npm cache clean --force 2>/dev/null
rm -rf package-lock.json node_modules/.cache 2>/dev/null

# 4. SQLite Vacuum (Compressing Structural Capital)
echo "[4/4] Vacuuming Databases..."
for db in *.db; do
    if [ -f "$db" ]; then
        sqlite3 "$db" "VACUUM;" 2>/dev/null
    fi
done

echo "[C5-REAL] Exergy x10 Purge Complete. Signal density maxed."
