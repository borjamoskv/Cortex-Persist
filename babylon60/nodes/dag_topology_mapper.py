#!/usr/bin/env python3
import json
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

db_path = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/moskv1_skills.db")

def generate_dag_map():
    if not db_path.exists():
        print("Database no encontrada.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, dependencies, validation_status, hash FROM autodidact_exergy_nodes ORDER BY idx ASC")
        nodes = cursor.fetchall()
        
        print("```mermaid")
        print("graph TD")
        print("    %% MOSKV-1 AUTODIDACT - DAG TOPOLOGY")
        print("    classDef validated fill:#0A0A0A,stroke:#2B3BE5,stroke-width:2px,color:#FFF;")
        print("    classDef pending fill:#222,stroke:#FF3333,stroke-width:2px,color:#FFF;")
        
        for row in nodes:
            node_id, name, deps_json, status, n_hash = row
            deps = json.loads(deps_json)
            
            clean_id = node_id.replace("-", "_")
            css_class = "validated" if status == "VALIDATED" else "pending"
            
            print(f'    {clean_id}["{node_id}<br>{name}<br>Hash: {n_hash}"]:::{css_class}')
            
            for dep in deps:
                clean_dep = dep.replace("-", "_")
                print(f"    {clean_dep} --> {clean_id}")
                
        print("```")
    except Exception as e:
        print(f"Error extrayendo DAG: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_dag_map()
