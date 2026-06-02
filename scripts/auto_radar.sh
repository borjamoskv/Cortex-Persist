#!/bin/zsh
# ==========================================
# CORTEX PERSIST: MAFIA AI RADAR (MAC AUTOMATION)
# Reality Level: C5-REAL
# Target: Keyboard Maestro / Automator / Cron
# ==========================================

# 1. Inyectar PATH (Keyboard Maestro ejecuta en un entorno limpio sin dotfiles)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export HOME="/Users/borjafernandezangulo"

# 2. Navegar al núcleo CORTEX
cd "$HOME/10_PROJECTS/cortex-persist" || exit 1

echo "[*] INICIANDO MAFIA-AI-RADAR (AUTOMATIZADO)..."

# 3. Ejecutar pipeline completo (ignoramos dependencias inline si uv ya las cacheó, pero las forzamos por seguridad)
uv run --with feedparser --with networkx --with requests python scripts/extractor_grafo_reputacion.py
uv run --with networkx --with requests python scripts/calculadora_smoke_index.py
uv run python scripts/alpha_extractor_c5.py

# 4. Reconstruir la lista negra de la Extensión Web
uv run python extensions/mafia-ai-blocker/build_blacklist.py

# 5. Cristalizar estado en Git (Silencioso para no romper Keyboard Maestro si no hay cambios)
git add data/reputation_graph/ scripts/ extensions/mafia-ai-blocker/
git commit -m "chore(cortex): auto-radar cristaliza topologia y actualiza firewall web" || true

echo "[*] PIPELINE COMPLETADO. FIREWALL WEB ACTUALIZADO."
