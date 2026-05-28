#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime
from typing import List, Dict

# Configuración Termodinámica
BASE_DIR = os.path.expanduser("~/Cortex-Persist/engine-c5")
TARGETS_DIR = os.path.join(BASE_DIR, "targets")
LEDGER_PATH = os.path.join(BASE_DIR, "vanguard_ledger.json")
HEARTBEAT_SEC = 3600  # 1 hora entre ciclos de escaneo completo

def log(msg: str, tier: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tier}] [VANGUARD-DAEMON] {msg}")

def update_ledger(target: str, status: str, details: str = "") -> None:
    ledger = {}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger = json.load(f)
        except:
            ledger = {}
    
    ledger[target] = {
        "last_seen": datetime.now().isoformat(),
        "status": status,
        "details": details
    }
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)

async def run_step(name: str, cmd: List[str], cwd: str = BASE_DIR) -> str:
    log(f"Iniciando fase: {name}", "EXEC")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode().strip() + stderr.decode().strip()
    
    if process.returncode == 0:
        log(f"Fase {name} completada con éxito.", "SUCCESS")
    else:
        log(f"Fase {name} reportó anomalías (ExitCode: {process.returncode}).", "WARN")
    
    return output

async def vanguard_cycle():
    log("=== INICIANDO CICLO DE EXTRACCIÓN VANGUARD-OMEGA ===", "SINGULARITY")
    
    # 1. SCOUT: Ingesta de Immunefi
    log("Ejecutando Scout L4 para actualizar targets...", "STEP")
    await run_step("IMMUNEFI-SCOUT", ["python3", "cortex_immunefi_scout.py"])
    
    # Leer targets reales
    targets_json = os.path.join(BASE_DIR, "real_bounties.json")
    if not os.path.exists(targets_json):
        log("Error crítico: No se encontró real_bounties.json", "ERROR")
        return

    with open(targets_json, "r") as f:
        targets_data = json.load(f)

    for target_info in targets_data:
        name = (target_info.get("protocol") or target_info.get("target") or "Unknown").replace(" ", "_").lower()
        target_path = os.path.join(TARGETS_DIR, name)
        
        if not os.path.exists(target_path):
            log(f"Target {name} no ha sido clonado aún. Saltando.", "SKIP")
            continue

        log(f"Asaltando target: {name.upper()}...", "ATTACK")
        
        # 2. FRACTOR: Análisis AST
        out_ast = await run_step(f"AST-{name}", ["python3", "cortex_ast_fractor.py", target_path])
        
        # 3. CHAOS: Fuzzing Persistente (250,000 runs)
        # Limitado a 60s por forge interno, pero el daemon espera
        out_chaos = await run_step(f"CHAOS-{name}", ["python3", "cortex_chaos_fuzzer.py", target_path, "50000"])
        
        # 4. LEDGER: Registro de resultados
        status = "FRACTURED" if "BREAKER" in out_chaos else "RESISTANT"
        update_ledger(name, status, out_chaos[-500:]) # Guardar el final del log
        
        if status == "FRACTURED":
            log(f"!!! COLISIÓN DETECTADA EN {name.upper()} !!!", "CRITICAL")
            # Aquí podrías añadir un Beacon de notificación (Telegram/Webhook)

    log(f"Ciclo completado. Entrando en hibernación por {HEARTBEAT_SEC}s...", "IDLE")

async def main():
    if "--once" in sys.argv:
        await vanguard_cycle()
        return

    while True:
        try:
            await vanguard_cycle()
        except Exception as e:
            log(f"Falla en el motor central: {e}", "FATAL")
        
        await asyncio.sleep(HEARTBEAT_SEC)

if __name__ == "__main__":
    asyncio.run(main())
