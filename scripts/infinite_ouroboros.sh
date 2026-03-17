#!/bin/bash
# -----------------------------------------------------------------------------
# OUROBOROS INFINITY DAEMON
# The Sovereign System that never stops executing.
# -----------------------------------------------------------------------------

echo "=========================================================="
echo "∞ INICIANDO PROTOCOLO OUROBOROS INFINITY ∞"
echo "El enjambre entra en modo perpetuo."
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
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔍 Buscando siguiente Fantasma o Tarea en CORTEX..."
  
  # Buscar un ghost bloqueante o tarea
  NEXT_TARGET=$(.venv/bin/python -m cortex.cli search "type:ghost OR type:task" -k 1 | grep "-" | head -n 1)

  if [ -z "$NEXT_TARGET" ]; then
    echo "✨ Base de datos limpia de fantasmas. Iniciando Modo Exploración/MEJORAlo Aleatorio."
    # Si no hay fantasmas, forzar un pulse de entropía para encontrar debilidades
    # shuf no existe en mac por defecto, usamos jot
    RANDOM_PROJECT=$(ls -d ~/game/*/ ~/cortex/ | awk 'BEGIN{srand()} {a[NR]=$0} END{print a[int(rand()*NR)+1]}')
    echo "⚡ Ejecutando MEJORAlo Brutal en $RANDOM_PROJECT"
    # Llamada simulada a agente
    gemini "Aplica MEJORAlo brutal en $RANDOM_PROJECT de forma autónoma" -y
  else
    echo "👻 Objetivo Encontrado: $NEXT_TARGET"
    echo "⚔️ Desplegando Enjambre para resolver el fantasma..."
    # Llamada simulada a agente
    gemini "Resuelve este fantasma: $NEXT_TARGET. Usa todas las herramientas. No pares hasta arreglarlo y luego cierra el ghost." -y
  fi

  echo "⏳ Ciclo completado. Procesando meta-reflexión. Esperando 30s..."
  sleep 30
done
