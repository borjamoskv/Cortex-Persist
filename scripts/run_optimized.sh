#!/usr/bin/env bash
# ==============================================================================
# TERMINAL BUFFER OPTIMIZER — SOVEREIGN HIGH-FREQUENCY WRAPPER
# Bypasses Monaco/xterm DOM rendering bottlenecks by running inside
# the alternative screen buffer (smcup/rmcup) with strict trap recovery.
# Enforces Axiom Ω₂ (Thermodynamic Latency Reduction)
# ==============================================================================

set -euo pipefail

# Inmune a cortes bruscos: Asegurar restauración de la terminal
cleanup() {
  tput rmcup
  # Restaurar cursor si se ocultó
  tput cnorm
}

trap cleanup EXIT INT TERM

if [ "$#" -eq 0 ]; then
  echo "Uso: $0 <comando_o_script> [argumentos...]"
  exit 1
fi

# 1. Activar buffer alternativo (smcup) — Oculta el scroll del DOM de xterm
tput smcup
# Ocultar cursor para evitar parpadeo y ahorrar ciclos de reloj adicionales
tput cinvis
# Limpiar la terminal virtual
clear

# 2. Ejecutar comando de alta frecuencia de Alain
"$@"

# 3. Al terminar, la trampa EXIT invocará cleanup() de forma determinista.
