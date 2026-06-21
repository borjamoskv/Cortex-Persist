#!/bin/bash
set -euo pipefail
# MULTIPLIER: x10 (Centuria Deep Purge)
# TARGET: Ultimate Entropy Annihilation

echo "[C5-REAL] Initiating Exergy x10 Deep Purge..."

cd /Users/borjafernandezangulo/10_PROJECTS/cortex-persist

# 1. Python Dead Weight Annihilation
echo "[1/4] Purging PyCache & Test Entropy..."
find . \( -name .venv -o -name .git -o -name node_modules \) -prune -o -type d -name "__pycache__" -exec rm -rf {} + || true
find . \( -name .venv -o -name .git -o -name node_modules \) -prune -o -type d -name ".pytest_cache" -exec rm -rf {} + || true
find . \( -name .venv -o -name .git -o -name node_modules \) -prune -o -type d -name ".ruff_cache" -exec rm -rf {} + || true
find . \( -name .venv -o -name .git -o -name node_modules \) -prune -o -type d -name ".mypy_cache" -exec rm -rf {} + || true
find . \( -name .venv -o -name .git -o -name node_modules \) -prune -o -type f -name "*.pyc" -delete || true

# 2. Rust Cargo Anergy Annihilation
echo "[2/4] Purging Rust Build Artifacts..."
if [ -d "cortex_rs" ]; then
    (cd cortex_rs && cargo clean) || true
fi

# 3. Node/NPM Entropy Annihilation
echo "[3/4] Purging NPM Cache..."
npm cache clean --force >/dev/null 2>&1 || true
rm -rf package-lock.json node_modules/.cache >/dev/null 2>&1 || true

# 4. SQLite Vacuum (Compressing Structural Capital)
echo "[4/4] Vacuuming Databases..."
for db in *.db; do
    if [ -f "$db" ]; then
        sqlite3 "$db" "VACUUM;" >/dev/null 2>&1 || true
    fi
done

echo "[C5-REAL] Exergy x10 Purge Complete. Signal density maxed."
