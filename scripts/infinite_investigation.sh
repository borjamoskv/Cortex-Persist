#!/bin/bash
# -----------------------------------------------------------------------------
# INFINITE INVESTIGATION DAEMON (DISEKTV / OSINT)
# The Sovereign System that never stops researching and auditing.
# -----------------------------------------------------------------------------

echo "=========================================================="
echo "∞ INICIANDO BUCLE INFINITO DE INVESTIGACIÓN ∞"
echo "El enjambre entra en modo auditoría/OSINT perpetua."
echo "=========================================================="

cd ~/cortex

# -- SECURITY GUARD --
if [[ -z "${CORTEX_ALLOW_INFINITE}" ]]; then
    echo -e "\033[38;2;255;0;0m[SECURITY] Script requires CORTEX_ALLOW_INFINITE=1 to run.\033[0m"
    exit 1
fi

MAX_CYCLES=${MAX_CYCLES:-50}
CYCLE=0

# Bucle con límite de seguridad
while [ $CYCLE -lt $MAX_CYCLES ]; do
  CYCLE=$((CYCLE + 1))
  echo "[CYCLE $CYCLE/$MAX_CYCLES]"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔍 Buscando siguiente objetivo de investigación..."
  
  # Seleccionamos un objetivo aleatorio de los proyectos para investigar a fondo
  RANDOM_PROJECT=$(ls -d ~/game/*/ ~/cortex/ | awk 'BEGIN{srand()} {a[NR]=$0} END{print a[int(rand()*NR)+1]}')
  
  echo "⚡ Iniciando investigación profunda (DISEKTV-1 / OSINT) en: $RANDOM_PROJECT"
  
  # Llamada al agente para que haga una investigación profunda sin detenerse
  # Le pedimos que analice vulnerabilidades, bugs ocultos, y arquitectura
  gemini "Entra en modo DISEKTV-1. Haz una investigación forense profunda de $RANDOM_PROJECT. Busca problemas de arquitectura, vulnerabilidades de seguridad, y código muerto. No pares hasta encontrar algo de valor. Usa todas las herramientas necesarias. Al terminar, guarda las conclusiones importantes en CORTEX." -y
  
  echo "⏳ Ciclo de investigación completado. Procesando meta-reflexión. Esperando 60s..."
  sleep 60
done
