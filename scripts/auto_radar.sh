#!/bin/zsh
# SYS_ID: CORTEX_RADAR_OMEGA
# MODE: C5-REAL

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export HOME="~"

cd "$HOME/10_PROJECTS/cortex-persist" || exit 1

uv run --with feedparser --with networkx --with requests python scripts/extractor_grafo_reputacion.py
uv run --with networkx --with requests python scripts/calculadora_smoke_index.py
uv run python scripts/alpha_extractor_c5.py
uv run python extensions/mafia-ai-blocker/build_blacklist.py

git add data/reputation_graph/ scripts/ extensions/mafia-ai-blocker/
git commit -m "chore(cortex): auto-radar sync" || true
