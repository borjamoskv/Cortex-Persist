#!/usr/bin/env python3
"""
∴ CORTEX-PROD-STRIKE v1.0
Ejecución masiva del motor Hound-Omega v7.3 sobre objetivos reales del Ledger.
"""

from db import init_db, get_bounties
from strike_engine import execute_strike
import os

def main():
    print("∴ CORTEX-PROD-STRIKE ACTIVE — TARGETING REAL EXERGY")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Asegurar API Key
    if not os.getenv("GEMINI_API_KEY"):
        print("[!] GEMINI_API_KEY missing. Aborting.")
        return

    init_db()
    import concurrent.futures

    # 1. Recuperar objetivos VIP, ampliando a 100 para Swarm masivo
    targets = get_bounties(status='found', min_exergy=1.0, limit=100)
    
    if not targets:
        print("[○] No high-exergy targets in local ledger. Scanning public network...")
        return

    print(f"[◈] INICIANDO SWARM: 100 AGENTES SOBRE {len(targets)} OBJETIVOS")
    
    def worker(t):
        title = t['title'].lower()
        category = "SECURITY"
        color = "\033[38;2;43;59;229m" # BLUE
        
        if any(k in title for k in ["mev", "jito", "arb"]):
            category = "MEV/ARTEMIS"
            color = "\033[38;2;0;255;136m" # GREEN
        elif any(k in title for k in ["recruit", "mercor", "talent"]):
            category = "BPO/MERCOR"
            color = "\033[38;2;102;0;255m" # VIOLET

        print(f"\n{color}[{category}]{'\033[0m'} ◈ Swarm Agent assigned to: {t['title']} (Exergia: {t['exergy']})")
        
        execute_strike(
            source_name=t['source'],
            title=t['title'],
            html_url=t['url'],
            exergy=t['exergy'],
            bounty_id=t['id']
        )

    # Launch Swarm
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        executor.map(worker, targets)

if __name__ == "__main__":
    main()
