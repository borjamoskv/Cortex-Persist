#!/usr/bin/env python3
"""
∴ CORTEX-FIREDANCER-LOOP v1.0
Persistent extraction loop for the $1,000,000 Firedancer bounty.
"""

import time
import subprocess
import sys
from pathlib import Path

# Fix python paths for Cortex script imports
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.append(str(SCRIPTS_DIR))

def run_iteration():
    print("\n" + "="*60)
    print(f"∴ FIREDANCER STRIKE ITERATION: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 1. Execute the production strike orchestrator
        # This will pick up the Firedancer target from the ledger
        subprocess.run(["python3", str(SCRIPTS_DIR / "prod_strike.py")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Iteration failed: {e}")
    except Exception as e:
        print(f"[!] Error: {e}")

def main():
    print("🚀 OUROBOROS LOOP ACTIVE: TARGET FIREDANCER v1.0")
    print("Law Ω₀: Silicon Truth Mandate Enabled.")
    
    try:
        while True:
            run_iteration()
            
            # Law Ω₂: Thermodynamics. Avoid burning exergy (CPU/Tokens) too fast.
            # 5 minute cooldown between full strike scans (or adjust as needed)
            print("\n[○] Cooling down for 300s (Exergy Balancing)...")
            time.sleep(300)
    except KeyboardInterrupt:
        print("\n[!] Loop terminated by operator.")

if __name__ == "__main__":
    main()
