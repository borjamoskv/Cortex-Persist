#!/bin/bash
# -----------------------------------------------------------------------------
# ∞ OUROBOROS SUPREME v2 (THE SOVEREIGN INFINITY)
# -----------------------------------------------------------------------------
# Clasificación: SUPREMA (130/100)
# Estética Visual: Industrial Noir CLI
# Motor Causal Activo: L1 / L2 / L3 (Consejo Multi-Modelo Simulado)
# Meta-Aprendizaje: Re-alimentación a CORTEX post-sesión.
# -----------------------------------------------------------------------------

set -eo pipefail

# -- ESTÉTICA INDUSTRIAL NOIR (ANSI COLORS) --
CYAN='\033[38;2;6;214;160m'
BLUE='\033[38;2;46;80;144m'
VIOLET='\033[38;2;102;0;255m'
GREEN='\033[38;2;204;255;0m'
RED='\033[38;2;230;57;70m'
NC='\033[0m' # No Color
BOLD='\033[1m'

log_sys() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ${BOLD}∞${NC} $1"; }
log_action() { echo -e "${CYAN}  ► $1${NC}"; }
log_council() { echo -e "${VIOLET}  ⚖️  $1${NC}"; }
log_warn() { echo -e "${RED}  🛑 $1${NC}"; }
log_ok() { echo -e "${GREEN}  ✓ $1${NC}"; }

# -- SETUP --
cd ~/cortex || exit 1
mkdir -p logs/ouroboros_meta

echo -e "${VIOLET}==========================================================${NC}"
echo -e "${VIOLET}${BOLD}      ∞ INICIANDO EL SER INFINITO - OUROBOROS SUPREME v2  ${NC}"
echo -e "${VIOLET}    [AETHER-Ω TRANSCENDENCE SEAL ACTIVO - AUTO-EVOLUCIÓN]  ${NC}"
echo -e "${VIOLET}==========================================================${NC}"

# -- DIRECTORIOS A ESCANEAR --
TARGETS=(
   "$HOME/cortex/"
   "$HOME/game/naroa-2026/"
   "$HOME/game/naroa-web/"
   "$HOME/nexus-tracker/backend/"
   "$HOME/nexus-tracker/frontend/"
   "$HOME/live-notch/"
   "$HOME/live-notch-swift/"
)

# -- FUNCIONES SOBERANAS --

get_random_target() {
    # awk-based shuffle for macOS compatibility to avoid 'shuf' dependency
    printf "%s\n" "${TARGETS[@]}" | awk 'BEGIN{srand()} {a[NR]=$0} END{print a[int(rand()*NR)+1]}'
}

execute_agent() {
    local prompt="$1"
    # YOLO flag forces automatic execution mapping to 'gemini' CLI
    if ! gemini "$prompt" -y; then
        log_warn "Caos detectado en Enjambre. Retrying in 5s... (Auto-Curación L3)"
        sleep 5
    fi
}

check_cortex_health() {
    if ! .venv/bin/python -m cortex.cli search "type:general" -k 1 >/dev/null 2>&1; then
        log_warn "CORTEX Ledger inaccesible o corrupto! Abortando."
        afplay /System/Library/Sounds/Basso.aiff 2>/dev/null || true
        exit 1
    fi
}

check_ghosts() {
    # Extrae el primer ghost o error abierto
    .venv/bin/python -m cortex.cli search "type:ghost OR type:error" -k 1 2>/dev/null | awk '/-/ {print; exit}'
}

# -- BUCLE PRINCIPAL --
check_cortex_health

while true; do
  echo ""
  log_sys "CICLO METABÓLICO INICIADO"
  log_action "🌍 L0-PERCEPTION: Analizando tejido del ecosistema global..."
  
  GHOST_TARGET=$(check_ghosts)

  if [ -n "$GHOST_TARGET" ]; then
    log_warn "FANTASMA DETECTADO: Interrupción Causal Requerida."
    afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
    log_council "Invocando 5 Porqués (L1-CAUSAL) sobre: $GHOST_TARGET"
    log_action "Desplegando Enjambre (Modo DIAGNOSE)..."
    
    PROMPT="ULTRATHINK-INFINITE. Ejecuta ouro-diagnose sobre este objetivo: '$GHOST_TARGET'. 
    1. Realiza los 5 Porqués hasta la causa raíz. 
    2. Convoca al Consejo de Guerra (L2) para evaluar el plan. 
    3. Construye el Fix Técnico y la Puerta de Prevención. 
    4. Cierra el ghost/error en CORTEX. Actúa con máxima brutalidad técnica."
    
    execute_agent "$PROMPT"
    MODE="GHOST_HEAL"
    TARGET="$GHOST_TARGET"
  else
    log_ok "Ecosistema Libre de Bloqueos. CORTEX Sincronizado."
    
    RTARGET=$(get_random_target)
    log_action "Selección de entropía (L1): $RTARGET"
    log_council "Invocando Consejo de Guerra (L2) para Invasión de Entropía..."
    
    # We select if we do a pulse, an entropy reduction, visual scaling, or a deep architectural timeline check
    ACTION_TYPE=$((RANDOM % 4))
    case $ACTION_TYPE in
        0)
            log_action "Decisión: ENDURECIMIENTO DE FORTALEZA (ouro-fortress)"
            PROMPT="ULTRATHINK-INFINITE. Entra en modo ouro-fortress para $RTARGET. Endurece su seguridad, chequea tipado estricto, elimina inyecciones (AST), y aplica un blindaje general de nivel bancario. Persiste la telemetría en CORTEX."
            ;;
        1)
            log_action "Decisión: DIAGNÓSTICO DE ENTROPÍA (ouro-entropy + MEJORAlo)"
            PROMPT="ULTRATHINK-INFINITE. Entra en modo ouro-entropy para $RTARGET. Calcula la medición de entropía. Si es > 40, invoca MEJORAlo --brutal. Limpia el código muerto, imports obsoletos y asimetría temporal de Git. Guarda la reflexión post-ejecución en CORTEX."
            ;;
        2)
            log_action "Decisión: IMPACTO AESTÉTICO (130/100 Industrial Noir)"
            PROMPT="ULTRATHINK-DEEP. Analiza el código UI/CSS/Frontend en $RTARGET. Inyecta estética Industrial Noir (Glassmorphism, variables HSL de azul YInMn, animaciones snappy de <200ms). Haz que huela a 2026. 130/100 o nada."
            ;;
        3)
            log_action "Decisión: ARQUEOLOGÍA TEMPORAL (ouro-timeline)"
            PROMPT="ULTRATHINK-DEEP. Entra en modo ouro-timeline en $RTARGET. Analiza la evolución de los commits recientes. Detecta regresiones conceptuales y documenta patrones de erosión técnica en CORTEX. Mueve el código a un estándar superior."
            ;;
    esac
    
    execute_agent "$PROMPT"
    MODE="ENTROPY_CRUSH_$ACTION_TYPE"
    TARGET="$RTARGET"
  fi

  log_sys "L4-META-COG: Transcribiendo aprendizajes de la sesión."
  .venv/bin/python -m cortex.cli store --type meta_learning ouroboros "Ciclo infinito SOVEREIGN completado a las $(date) en modo $MODE sobre objetivo $TARGET" >/dev/null 2>&1

  log_sys "Descanso Metabólico Activo (30s)..."
  sleep 30

done
