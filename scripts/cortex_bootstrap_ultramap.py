import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import json
import hashlib
import time
import os

DB_PATH = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex_runtime_evidence.db"

ULTRAMAP = {
    "OUROBOROS-∞": "AX-047",
    "Thermodynamic-Context-Compression-OMEGA": "AX-042",
    "Epistemic-Purge-OMEGA": "L2-Ω5",
    "SOTA-Vector-Engine-Omega": "L4-Δ3",
    "LEA-OMEGA": "AX-041",
    "ANTIGRAVITY-GITHUB-OMEGA": "AX-041",
    "Cortex-Omega-ATMS-OMEGA": "AX-045",
    "Vesicular-Runtime-Omega": "L3-Σ1",
    "Frontier-RevEng-OMEGA": "AX-046",
    "Mac-Control-Ω": "L1-Φ5",
    "Algorithmic-Music-OMEGA": "L3-Σ3",
    "Bounty-Exergy-Extractor-OMEGA": "L4-Δ1",
    "Browser-CDP-Automation-OMEGA": "L4-Δ2",
    "Sortu-APEX": "AX-046"
}

def bootstrap():
    print("[C5-REAL] Iniciando colapso físico de ULTRAMAP en motor causal...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Ejecutamos modo WAL para tolerar concurrencia (R10)
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA busy_timeout=5000;")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS epistemic_ultramap (
            hash TEXT PRIMARY KEY,
            skill TEXT,
            axiom TEXT,
            babylon_timestamp INTEGER
        )
    """)
    
    # Base-60 time (L3-Babylon-60 rule)
    b_time = int(time.time() * 60)
    
    inserted = 0
    for skill, axiom in ULTRAMAP.items():
        payload = f"{skill}:{axiom}:{b_time}".encode()
        node_hash = hashlib.sha256(payload).hexdigest()
        
        try:
            cur.execute("INSERT INTO epistemic_ultramap (hash, skill, axiom, babylon_timestamp) VALUES (?, ?, ?, ?)",
                        (node_hash, skill, axiom, b_time))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    
    # Ledger update simulation
    ledger_hash = hashlib.sha256(str(b_time).encode()).hexdigest()
    print(f"[C5-REAL] Colapso completado. {inserted} nodos epistémicos cristalizados en SQLite WAL.")
    print(f"[C5-REAL] Ledger Hash: {ledger_hash}")
    print(f"[C5-REAL] Cero Anergía. Grafo Inmutable Alcanzado.")

if __name__ == "__main__":
    bootstrap()
