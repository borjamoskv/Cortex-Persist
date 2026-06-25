import re
import hashlib
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
from pathlib import Path

# Configuración C5-REAL (BABYLON-60)
DB_PATH = Path("cortex_ontology.db")
TIMEOUT_MS = 5000

def compute_hash(term: str, definition: str) -> str:
    """Genera la firma criptográfica del nodo."""
    payload = f"{term.strip()}::{definition.strip()}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def compile_ontology(file_path: Path):
    """Parsea el texto C4-SIM y lo cristaliza en SQLite C5-REAL."""
    with sqlite3.connect(DB_PATH, timeout=TIMEOUT_MS/1000.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS epistemic_nodes (
                node_hash TEXT PRIMARY KEY,
                category TEXT,
                term TEXT,
                definition TEXT,
                exergy_level INTEGER DEFAULT 5
            )
        """)
        
        raw_text = file_path.read_text(encoding="utf-8")
        
        # Regex estructural para Bloques y Términos
        block_pattern = re.compile(r"###\s+(.+)")
        term_pattern = re.compile(r"\d+\.\s+\*\*([^:]+):\*\*\s+(.+)")
        
        current_category = "UNKNOWN"
        nodes_inserted = 0
        
        for line in raw_text.splitlines():
            block_match = block_pattern.match(line)
            if block_match:
                current_category = block_match.group(1).strip()
                continue
                
            term_match = term_pattern.match(line)
            if term_match:
                term = term_match.group(1).strip()
                definition = term_match.group(2).strip()
                node_hash = compute_hash(term, definition)
                
                try:
                    conn.execute(
                        "INSERT INTO epistemic_nodes (node_hash, category, term, definition) VALUES (?, ?, ?, ?)",
                        (node_hash, current_category, term, definition)
                    )
                    nodes_inserted += 1
                except sqlite3.IntegrityError:
                    pass # Evitar redundancia entrópica
                    
        conn.commit()
        print(f"[C5-REAL] Cristalización completada. {nodes_inserted} Nodos Epistémicos inyectados en {DB_PATH}.")

if __name__ == "__main__":
    ontology_path = Path("ontology_raw.md")
    if ontology_path.exists():
        compile_ontology(ontology_path)
    else:
        print(f"ERROR: {ontology_path} no encontrado. Inyecte la entropía primero.")
