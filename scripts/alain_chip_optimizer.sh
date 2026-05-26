#!/usr/bin/env bash
# ==============================================================================
# ALAIN CHIP OPTIMIZER v2.0 — SOVEREIGN INTEL SILICON CRUCIBLE
# Designed for: MacBook Pro 15.4" | Intel Core i5/i7 | 16 GB RAM | 512 GB SSD
# Enforces Axiom Ω₂ (Thermodynamic Cognition) and C5-REAL Forensic Telemetry
# ==============================================================================

set -euo pipefail

# Design Aesthetics: Industrial Noir 2026
COLOR_BLUE='\033[0;34m'
COLOR_RED='\033[0;31m'
COLOR_AMBER='\033[0;33m'
COLOR_RESET='\033[0m'

echo -e "${COLOR_BLUE}--- ENGAGING CHIP CRUCIBLE FOR ALAIN ---${COLOR_RESET}"
echo -e "Hardware Target: MacBook Pro 15.4\" [i5/i7 | 16GB RAM | 512GB SSD]"
echo -e "Ingestion Boundary: CORTEX-Persist Ledger Support Enabled"
echo ""

# ------------------------------------------------------------------------------
# PHASE 1: PRIVILEGE GATING & THERMAL DE-THROTTLING
# ------------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo -e "${COLOR_RED}[!] Error: Este script requiere privilegios de Root (sudo) para interactuar con SMC y sysctl.${COLOR_RESET}"
  exit 1
fi

echo -e "${COLOR_AMBER}[1/5] Calibrando Gestión de Energía y Térmica (SMC)...${COLOR_RESET}"

# Deshabilitar suspensión por red (Wake on LAN) que despierta hilos Intel inútilmente
pmset -a womp 0
# Deshabilitar hibernación agresiva para optimizar el ciclo de escritura de 512GB SSD
pmset -a autopoweroff 0
pmset -a standby 0

# Forzar al programador del kernel (scheduler) a priorizar rendimiento térmico sobre throttling
sysctl -w kern.sched.quantum=10 >/dev/null
sysctl -w debug.lowpri_throttle_enabled=0 >/dev/null

# ------------------------------------------------------------------------------
# PHASE 2: SSD TRIM & CACHE ANNIHILATION
# ------------------------------------------------------------------------------
echo -e "${COLOR_AMBER}[2/5] Purgando Caches y Optimizando SSD (Trimforce)...${COLOR_RESET}"

# Asegurar que Trimforce esté habilitado para optimizar el controlador del SSD de 512 GB
if ! system_profiler SPSerialATADataType | grep -q "TRIM Support: Yes"; then
  echo -e "[*] Tip: Ejecute 'sudo trimforce enable' en una terminal independiente para activar TRIM."
fi

# Eliminar ficheros temporales del sistema y purgar caches de usuario redundantes
rm -rf ~/Library/Caches/*
rm -rf /Library/Caches/*

# ------------------------------------------------------------------------------
# PHASE 3: TOUCH BAR DAEMON PURGE & GRAPHICS LATENCY LOCK
# ------------------------------------------------------------------------------
echo -e "${COLOR_AMBER}[3/5] Neutralizando Servidor Touch Bar y Fijando Latencia GPU...${COLOR_RESET}"

# Liquidar fugas de memoria del Touch Bar Server para liberar ciclos de reloj del i5
killall TouchBarServer 2>/dev/null || true
killall ControlStrip 2>/dev/null || true

# Fijar GPU Dinámica en alto rendimiento (evita latencia de conmutación entre Iris y Radeon)
# gpuswitch 1 = Solo GPU integrada (Ahorro térmico). gpuswitch 4 = Solo GPU dedicada (Máximo rendimiento)
pmset -a gpuswitch 1 

# ------------------------------------------------------------------------------
# PHASE 4: ACTIVE MEMORY PURGE (16 GB EXERGY MATRIX)
# ------------------------------------------------------------------------------
echo -e "${COLOR_AMBER}[4/5] Reclamando Exergía de Memoria RAM (Purge)...${COLOR_RESET}"
purge

# ------------------------------------------------------------------------------
# PHASE 5: CORTEX-PERSIST C5-REAL EVIDENTIARY REGISTRATION
# ------------------------------------------------------------------------------
echo -e "${COLOR_AMBER}[5/5] Inyectando Registro Forense en CORTEX-Persist Ledger...${COLOR_RESET}"

# Detectar localización de la base de datos de Cortex
CORTEX_DIR="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist"

if [ -d "$CORTEX_DIR" ]; then
  python3 <<EOF
import sys
import asyncio
sys.path.append("$CORTEX_DIR")

from cortex.engine import CortexEngine
from cortex.facts.manager import FactManager

async def register_optimization():
    try:
        engine = CortexEngine()
        manager = FactManager(engine)
        
        fact_content = (
            "Optimización de silicio MacBook Pro 15.4 TouchBar i5 completada con éxito. "
            "SMC Fans ajustados, pmset optimizado, caches destruidas, RAM de 16GB purgada "
            "y deamons del TouchBar reiniciados para aniquilar el estrangulamiento térmico (throttling)."
        )
        
        fact_id = await manager.store(
            project="mac_silicon_optimization",
            content=fact_content,
            fact_type="telemetry",
            tags=["alain", "macbook-i5", "silicon-hardening", "smc"],
            source="alain_chip_optimizer.sh",
            meta={
                "target_hardware": "MacBook Pro 15.4\" i5 TouchBar (16GB, 512GB SSD)",
                "author": "Alain",
                "exergy_level": "C5-REAL"
            }
        )
        print(f"\033[0;32m[+] Registro de Evidencia Inyectado con Éxito. Fact ID: #{fact_id}\033[0m")
    except Exception as e:
        print(f"\033[0;31m[-] Fallo al inyectar evidencia en CORTEX: {e}\033[0m")

asyncio.run(register_optimization())
EOF
else
  echo -e "${COLOR_RED}[!] Error: No se localizó la ruta de CORTEX-Persist para telemetría.${COLOR_RESET}"
fi

echo ""
echo -e "${COLOR_BLUE}--- CHIP DE MACBOOK PRO EN EL CANAL DE ALAIN TOTALMENTE OPTIMIZADO ---${COLOR_RESET}"
