import asyncio
import time
import json
import os
import sqlite3
import subprocess
import hashlib
import sys
import base64
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cortex import CortexEngine
from cortex.engine.causal.taint_engine import generate_secure_taint_token

async def main():
    db_path = "cortex_runtime_evidence.db"
    key_path = Path(".moskv-1.key")
    
    for suffix in ["", "-wal", "-shm"]:
        path = db_path + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    if key_path.exists():
        with open(key_path, "rb") as f:
            priv_bytes = f.read()
        priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        print("[*] Loaded persistent Ed25519 identity for moskv-1.")
    else:
        print("[*] Generating new persistent Ed25519 identity for moskv-1...")
        priv_key = Ed25519PrivateKey.generate()
        with open(key_path, "wb") as f:
            f.write(priv_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
    pub_key = priv_key.public_key()
    
    priv_b64 = base64.b64encode(priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )).decode("ascii")
    
    pub_b64 = base64.b64encode(pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )).decode("ascii")

    engine = CortexEngine(db_path=db_path)
    
    # 1. Force schema initialization by triggering a dummy store (it will fail SAGA-1 but migrate the DB)
    try:
        await engine.store(project="init", content="init", fact_type="init", source="init")
    except Exception:
        pass

    # 2. Now the schema exists with all columns (reputation_score, etc). We can insert the agent.
    conn_sync = sqlite3.connect(db_path)
    conn_sync.execute("INSERT OR REPLACE INTO agents (id, name, public_key, is_active) VALUES (?, ?, ?, 1)", ("moskv-1", "MOSKV-1 Execution Kernel", pub_b64))
    conn_sync.commit()
    conn_sync.close()

    
    EVENTS_COUNT = 100
    print(f"[*] Registrando Agente y generando {EVENTS_COUNT} eventos causales firmados...")
    start_time = time.time()
    
    for i in range(EVENTS_COUNT):
        content_str = f"System telemetry causal payload event index {i} blockhash {hashlib.md5(str(i).encode()).hexdigest()}"
        project_str = "causal-demo"
        logos_sig = hashlib.sha256(f"{content_str}{project_str}".encode()).hexdigest()
        
        cortex_taint = generate_secure_taint_token(
            agent_id="moskv-1",
            session_id="demo-ses",
            content=content_str,
            private_key_b64=priv_b64
        )

        await engine.store(
            project=project_str,
            content=content_str,
            fact_type="telemetry",
            source="agent:moskv-1",
            actor_id="moskv-1",
            meta={
                "actor_id": "moskv-1",
                "logos_signature": logos_sig,
                "cortex_taint": cortex_taint
            }
        )
    
    # Final verify
    ledger_result = await engine.verify_ledger()
    ledger_ok = False
    final_hash = None
    if isinstance(ledger_result, dict):
        ledger_ok = ledger_result.get("valid", False)
    else:
        ledger_ok = bool(ledger_result)
        
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            final_hash = row[0]
    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)
    
    if not final_hash:
        raise RuntimeError("Ledger hash unavailable. verify_ledger no retornó un hash criptográfico válido.")

    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        git_commit = "unknown"
        
    try:
        git_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
    except Exception:
        git_tree = "unknown"
        
    try:
        status_out = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
        working_tree_clean = len(status_out) == 0
    except Exception:
        working_tree_clean = False

    def hash_file(filepath):
        h = hashlib.sha256()
        try:
            with open(os.path.abspath(filepath), "rb") as f:
                h.update(f.read())
            return h.hexdigest()
        except Exception:
            return "unknown"
            
    binary_hash = hash_file(sys.executable)
    script_hash = hash_file(__file__)

    output = {
        "runtime_lineage": {
            "git_commit": git_commit,
            "git_tree": git_tree,
            "working_tree_clean": working_tree_clean,
            "python_binary_hash": binary_hash,
            "script_hash": script_hash,
            "executed_by": "agent:moskv-1"
        },
        "ledger": {
            "events_processed": EVENTS_COUNT,
            "last_hash": final_hash,
            "verified": ledger_ok
        },
        "artifact": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "execution_time_ms": execution_time_ms,
            "manifest_reference": "deployment_manifest.yaml",
            "verification_method": "C5-REAL EDG V6"
        }
    }
    
    canonical_json = json.dumps(output, indent=2)
    
    with open("runtime_evidence.json", "w") as f:
        f.write(canonical_json)
        
    with open("runtime_evidence.json.sha256", "w") as f:
        f.write(hashlib.sha256(canonical_json.encode('utf-8')).hexdigest())
        
    print(f"[+] Evidencia sellada en runtime_evidence.json y su firma en runtime_evidence.json.sha256")
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
