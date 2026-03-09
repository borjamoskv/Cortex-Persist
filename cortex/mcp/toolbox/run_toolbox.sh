#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# CORTEX MCP Toolbox Launcher
#
# Starts the MCP Toolbox for Databases server against cortex.db.
# Prerequisites: install the toolbox binary:
#   go install github.com/googleapis/genai-toolbox@latest
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_FILE="${SCRIPT_DIR}/tools.yaml"
export CORTEX_DB="${CORTEX_DB:-${HOME}/.cortex/cortex.db}"
PORT="${TOOLBOX_PORT:-5000}"

# ── Preflight ─────────────────────────────────────────────────────────

if ! command -v toolbox &>/dev/null; then
    echo "❌ 'toolbox' binary not found in PATH."
    echo "   Install: go install github.com/googleapis/genai-toolbox@latest"
    exit 1
fi

if [[ ! -f "${CORTEX_DB}" ]]; then
    echo "❌ CORTEX database not found at: ${CORTEX_DB}"
    echo "   Set CORTEX_DB env var or ensure ~/.cortex/cortex.db exists."
    exit 1
fi

if [[ ! -f "${TOOLS_FILE}" ]]; then
    echo "❌ tools.yaml not found at: ${TOOLS_FILE}"
    exit 1
fi

# ── Launch ────────────────────────────────────────────────────────────

echo "🧠 CORTEX MCP Toolbox — Knowledge Membrane"
echo "   DB:    ${CORTEX_DB}"
echo "   Port:  ${PORT}"
echo "   Tools: ${TOOLS_FILE}"
echo ""

exec toolbox \
    --tools-file "${TOOLS_FILE}" \
    --port "${PORT}" \
    "$@"
