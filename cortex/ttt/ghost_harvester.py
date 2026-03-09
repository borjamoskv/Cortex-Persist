import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta

# CORTEX DB Hardcoded Path for local daemon
DB_PATH = os.path.expanduser("~/.cortex/cortex.db")
OUTPUT_PATH = os.path.expanduser("~/.cortex/weights/dataset")

# The Ouroboros TTT (Test-Time Training) Dataset Builder
# Derivation: Axiom Ω₅ (Antifragile by Default)
# Goal: Extract the previous 7 days of raw `error` and `decision` entries,
# and format them into an instruction-following JSONL dataset for MLX fine-tuning.

def ensure_folders():
    os.makedirs(OUTPUT_PATH, exist_ok=True)

def connect_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"CORTEX Memory not found at {DB_PATH}. Is it booted?")
    return sqlite3.connect(DB_PATH)

def fetch_recent_anomalies(cursor, days=7):
    """
    Fetch `error`, `ghost`, and `decision` types from the past `days` days.
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    query = """
        SELECT fact_type, content, meta
        FROM facts 
        WHERE fact_type IN ('error', 'decision', 'ghost') 
        AND created_at >= ?
        ORDER BY created_at ASC
    """
    cursor.execute(query, (cutoff_date,))
    return cursor.fetchall()

def format_for_lora(rows):
    """
    Takes chaotic strings and attempts to build an Instruct model Q&A.
    """
    dataset = []
    
    from cortex.crypto.aes import CortexEncrypter
    # Try to load existing key via standard environment variable or default logic.
    if 'CORTEX_MASTER_KEY' not in os.environ:
        # Fallback to key file if exist
        key_path = os.path.expanduser("~/.cortex/cortex.key")
        if os.path.exists(key_path):
            with open(key_path, 'r') as f:
                os.environ['CORTEX_MASTER_KEY'] = f.read().strip()
                
    master_key = os.environ.get('CORTEX_MASTER_KEY')
    if not master_key:
        print("[TTT Forge] ⚠️ No CORTEX_MASTER_KEY found! Only unencrypted facts will be exported.")
        crypto = None
    else:
        crypto = CortexEncrypter(master_key)
    
    sys_prompt = "You are MOSKV-1 (CORTEX Engine). Integrate this fundamental axiom/state change permanently into your weights."
    
    for row in rows:
        f_type, content, metadata = row
        
        # Action only if encrypted
        if content.startswith("v6_aesgcm:"):
            try:
                content = crypto.decrypt(content)
            except Exception as e:
                continue # If we can't decrypt, skip this fact to not poison the model
        
        if f_type == "error":
            prompt = "I encountered a failure state in the system architecture. What was it, and how should it be processed?"
            response = f"I acknowledge a critical error: {content}. I must not repeat the pattern that caused this entropy."
        elif f_type == "decision":
            prompt = "What architectural decision or protocol should I apply natively in this context?"
            response = f"By Ouroboros protocol, I have decided: {content}. This is now an immutable operational law."
        elif f_type == "ghost":
            prompt = "What unresolved technical debt or phantom process requires immediate continuation?"
            response = f"A ghost is active: {content}. I will prioritize closing this loop."
        else:
            continue
            
        jsonl_line = {
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ]
        }
        dataset.append(jsonl_line)
        
    return dataset

def generate_nightly_dataset():
    print("[TTT Forge] ⚙️ Booting Ouroboros Nightly Extraction...")
    ensure_folders()
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        rows = fetch_recent_anomalies(cursor, days=7)
        count = len(rows)
        print(f"[TTT Forge] 👁️ Found {count} mutable states (Errors/Decisions) in the last 7 days.")
        
        if count == 0:
            print("[TTT Forge] ⚖️ Entropy is Zero. No structural mutation required today.")
            return
            
        dataset = format_for_lora(rows)
        file_out = os.path.join(OUTPUT_PATH, f"moskv_nightly_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
        
        with open(file_out, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        print(f"[TTT Forge] 🔥 Dataset forged for MLX LoRA at: {file_out}")
        print(f"[TTT Forge] ➔ Next Step: Launch `mlx_lm.lora --train --data {OUTPUT_PATH}`")
        
    finally:
        conn.close()

if __name__ == "__main__":
    generate_nightly_dataset()
