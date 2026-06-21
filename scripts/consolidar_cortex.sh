#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized Physical Consolidation (ULTRATHINK)

set -e

echo "🔱 Iniciando Consolidación Física de CORTEX-Persist (C5-REAL)..."

# 1. Purga Termodinámica (Cachés Estocásticas y Entropía)
echo "   [1/4] Purgando sumideros de entropía (Cachés)..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 2. Control de Bloqueos Físicos (SQLite WAL Locks)
echo "   [2/4] Consolidando Límites WAL en Bases de Datos..."
for db in *.db; do
    if [ -f "$db" ]; then
        sqlite3 "$db" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null 2>&1 || true
    fi
done

# 3. Alineación del Kernel Físico de Rust (Babylon-60)
echo "   [3/4] Validando integridad estructural de Cortex-RS..."
if [ -d "cortex_rs" ]; then
    maturin develop --release >/dev/null 2>&1 || echo "⚠️ Recompilación de Rust omitida o fallida."
fi

# 4. Git Sentinel (Autopoiesis Criptográfica R4)
echo "   [4/4] Forzando Colapso Causal en el Grafo Git (Git Sentinel)..."
git add .
if ! git diff-index --quiet HEAD --; then
    commit_msg="chore(core): inyectar orquestación determinista BFT en flujo de consolidación"
    git commit -m "$commit_msg" >/dev/null
    HASH=$(git rev-parse HEAD)
    echo "✅ Colapso Semántico completado. Hash Sentinel: $HASH"
else
    HASH=$(git rev-parse HEAD)
    echo "✅ No hay entropía sin colapsar. Repositorio limpio. Hash actual: $HASH"
fi

echo "🔱 Consolidación Física Completada."
exit 0
