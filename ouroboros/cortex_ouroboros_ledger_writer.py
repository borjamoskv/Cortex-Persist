import json
import os
from datetime import datetime

# CORTEX OUROBOROS LEDGER WRITER
# Persists extracted exergy into the Sovereign Vault.

LEDGER_PATH = "/Users/borjafernandezangulo/30_CORTEX/cortex_vault_ledger.json"

def write_to_ledger(yield_amount: float, vector: str, hash_proof: str):
    print(f"[\033[34mLEDGER_WRITE\033[0m] Persisting yield to {os.path.basename(LEDGER_PATH)}...")
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "yield_usd": yield_amount,
        "vector": vector,
        "proof_hash": hash_proof,
        "status": "CRYSTALLIZED"
    }
    
    data = []
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
                
    data.append(entry)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"[LEDGER_WRITE] Hash Consolidado: {hash_proof[:18]}...")
    print(f"[LEDGER_WRITE] Persistence: ABSOLUTE")

if __name__ == "__main__":
    # Mock entry from the recent simulation
    write_to_ledger(47250.64, "MEV-Mamba-v2", "63a9edaae7fc4b477342616e")
