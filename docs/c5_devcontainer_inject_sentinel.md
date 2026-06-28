#!/bin/bash
# ==============================================================================
# CORTEX SOVEREIGN DEVCONTAINER - INJECT_SENTINEL.SH TEMPLATE
# Target: Enforce Git Sentinel and CORTEX guards in container runtime
# Reality Level: C5-REAL
# ==============================================================================

set -euo pipefail

# 1. Configuración de Variables
CORTEX_DIR="/workspaces/cortex"
GIT_HOOKS_DIR="${CORTEX_DIR}/.git/hooks"
PRE_COMMIT_HOOK="${GIT_HOOKS_DIR}/pre-commit"

echo "[C5-REAL] Initializing CORTEX DevContainer post-creation setup..."

# 2. Verificación de Directorio Git
if [ ! -d "${CORTEX_DIR}/.git" ]; then
    echo "[C5-REAL] WARNING: .git directory not found. Initializing repository..."
    git init "${CORTEX_DIR}"
fi

mkdir -p "${GIT_HOOKS_DIR}"

# 3. Inyección del Hook Git Sentinel
echo "[C5-REAL] Injecting Git Sentinel Pre-Commit Hook..."

cat << 'EOF' > "${PRE_COMMIT_HOOK}"
#!/bin/bash
# CORTEX Git Sentinel Pre-Commit Guard (C5-REAL)
set -euo pipefail

echo "[C5-REAL] Running Git Sentinel Hooks..."

# Validar que no hay archivos temporales ni logs de depuración staged
GHOSTS=$(git diff --cached --name-only | grep -E '\.log$|\.tmp$|__pycache__/|dangling_' || true)
if [ -n "$GHOSTS" ]; then
    echo "❌ [C5-REAL] ABORT: Intento de comitear archivos entrópicos (logs/temporales):"
    echo "$GHOSTS"
    exit 1
fi

# Validar sintaxis AST básica (Python)
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
if [ -n "$PYTHON_FILES" ]; then
    echo "[C5-REAL] Validating AST syntax on staged Python files..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            python -m py_compile "$file" || {
                echo "❌ [C5-REAL] ABORT: Error de sintaxis AST en $file"
                exit 1
            }
        fi
    done
fi

echo "✅ [C5-REAL] Git Sentinel checks passed."
exit 0
EOF

chmod +x "${PRE_COMMIT_HOOK}"

# 4. Configuración de Identidad Git de Creador (Ley Γ1)
echo "[C5-REAL] Applying sovereign creator Git credentials..."
git config --local user.name "Borja Moskv"
git config --local user.email "borjamoskv@users.noreply.github.com"

# 5. Activación de SQLite WAL para persistencia asíncrona local (Regla R10)
if [ -f "${CORTEX_DIR}/cortex.db" ]; then
    echo "[C5-REAL] Enforcing WAL mode and busy_timeout on local SQLite state..."
    sqlite3 "${CORTEX_DIR}/cortex.db" "PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;"
fi

echo "[C5-REAL] Sovereign DevContainer environment successfully initialized."
