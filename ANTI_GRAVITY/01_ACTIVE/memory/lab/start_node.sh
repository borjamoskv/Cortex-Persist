#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized
# CORTEX-PERSIST SOVEREIGN NODE BOOTSTRAP
# Reality Level: C5-REAL

set -e

# Colors
CORTEX_BLUE="\033[38;2;43;59;229m"
CORTEX_RED="\033[38;2;255;50;50m"
RESET="\033[0m"

echo -e "${CORTEX_BLUE}[CORTEX-NODE] Bootstrapping Sovereign Epistemic Engine...${RESET}"

# 1. Compile Rust bindings via Maturin
echo -e "\n${CORTEX_BLUE}[1/3] Forging native Rust VSA (cortex_rs)...${RESET}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q maturin fastapi uvicorn pydantic
maturin develop --manifest-path cortex_rs/Cargo.toml --release

# 2. Reset Ledger State
echo -e "\n${CORTEX_BLUE}[2/3] Initializing Append-Only Ledger...${RESET}"
if [ -f "cortex_ledger.jsonl" ]; then
    rm cortex_ledger.jsonl
    echo -e "Old ledger purged."
fi

# 3. Launch the API Node
echo -e "\n${CORTEX_BLUE}[3/3] Launching FastAPI Sovereign Node (Port 8000)...${RESET}"
uvicorn cortex-core.server:app --reload --host 0.0.0.0 --port 8000
