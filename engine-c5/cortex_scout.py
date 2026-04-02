#!/usr/bin/env python3
import os
import sys
import subprocess
from datetime import datetime

TARGET_DIR = os.path.expanduser("~/Cortex-Persist/engine-c5/targets")

def log(msg, tier="INFO"):
    print(f"[{datetime.now().time()}] [{tier}] [SCOUT] {msg}")

def clone_audit_target(repo_url, protocol_name):
    """
    Fricción 0. Llama de consola directa al git de los audit competitions.
    """
    target_path = os.path.join(TARGET_DIR, protocol_name)
    if os.path.exists(target_path):
        log(f"Target '{protocol_name}' ya existe en el silo. Destruyendo entropía residual...", "WARN")
        subprocess.run(["rm", "-rf", target_path], check=True)
        
    log(f"Clonando vector C5-REAL desde: {repo_url}")
    try:
        # Clone with depth 1 for maximum speed and minimum storage (Exergy optimization)
        subprocess.run(["git", "clone", "--depth", "1", repo_url, target_path], check=True, capture_output=True)
        log(f"Exito. AST disponible en {target_path}", "SUCCESS")
        return target_path
    except subprocess.CalledProcessError as e:
        log(f"Fallo en clonado: {e.stderr.decode()}", "FATAL")
        sys.exit(1)

if __name__ == "__main__":
    log("Iniciando CORTEX Scout Dæmon (C5-REAL)...")
    # Injecting Live Day Zero Target from GitHub API
    live_repo = "https://github.com/code-423n4/2026-04-layerzero" 
    protocol = "2026-04-layerzero"
    clone_audit_target(live_repo, protocol)
