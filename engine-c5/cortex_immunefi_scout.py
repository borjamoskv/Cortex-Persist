#!/usr/bin/env python3
import os
import json
import asyncio
import urllib.request
import urllib.error
from typing import List, Dict, Optional
from datetime import datetime
import subprocess

def log(msg: str, tier: str = "INFO") -> None:
    print(f"[{datetime.now().time()}] [{tier}] [IMMUNEFI-SCOUT] {msg}")

async def fetch_open_bounties() -> List[Dict[str, str]]:
    """Captura los targets reales de Immunefi desde el JSON generado por el subagente."""
    path = os.path.expanduser("~/Cortex-Persist/engine-c5/real_bounties.json")
    log(f"Extrayendo targets reales desde: {path}", "EXTRACT")
    
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        else:
            log("No se encontró real_bounties.json. Hallucinando fallback seguro.", "WARN")
            return []
    except Exception as e:
        log(f"Error parseando real_bounties.json: {e}", "ERROR")
        return []

def clone_and_fracture(repo_url: str, target_name: str) -> bool:
    """Implementa el cierre del Ouroboros: Clona -> Extrae AST -> Prepara para Módulo Chaos"""
    name_clean = target_name.replace(' ', '_').lower()
    target_dir = os.path.expanduser(f"~/Cortex-Persist/engine-c5/targets/{name_clean}")
    
    if os.path.exists(target_dir):
        log(f"Repositorio {target_name} ya anclado. Refreshing...", "CACHE")
        # No borrar todo, solo git fetch/pull para ahorrar exergía
        try:
            subprocess.run(["git", "pull"], cwd=target_dir, capture_output=True)
            return True
        except:
             return True

    log(f"Extrayendo repositorio {target_name} ({repo_url})...", "CLONE")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir], 
            check=True, 
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        log(f"Falla crítica clonando repo: {e}", "ERROR")
        return False

async def orchestrate_l4_extraction() -> None:
    log("Iniciando Ouroboros Sovereign Pipeline (Scout → Fractor → Chaos)", "SYSTEM")
    targets = await fetch_open_bounties()
    
    if not targets:
        log("Sin targets para procesar. Abortando ciclo.", "ERROR")
        return

    os.makedirs(os.path.expanduser("~/Cortex-Persist/engine-c5/targets"), exist_ok=True)
    
    for t in targets:
        # Compatibility with different JSON keys from subagent/search
        name = t.get("protocol") or t.get("target") or "Unknown"
        reward = t.get("max_reward") or "N/A"
        url = t.get("repo_url") or t.get("url")
        
        if not url:
            log(f"Target {name} no tiene URL de repo. Saltando.", "WARN")
            continue

        log(f"Asignando Enjambre a Target: {name} | Bounty: {reward}", "L4-ROUTER")
        
        if clone_and_fracture(url, name):
            log(f"- [✓] Target Lock: {name}. Inyectando en matriz de Fuzzing.", "PIPELINE")

if __name__ == "__main__":
    asyncio.run(orchestrate_l4_extraction())

if __name__ == "__main__":
    asyncio.run(orchestrate_l4_extraction())
