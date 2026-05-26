import os
import json
import sqlite3
import time
from persistence import OutboxDaemon, DB_PATH

DUMMY_DIR = os.path.dirname(os.path.abspath(__file__))
DUMMY_FILE = os.path.join(DUMMY_DIR, "dummy_exergy.py")

def setup():
    with open(DUMMY_FILE, "w") as f:
        f.write("def calculate_exergy():\n    return 1.0\n")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM cortex_swarm_queue")
    conn.commit()
    conn.close()
    import time
    time.sleep(0.5)

def inject_task():
    new_source = "def calculate_exergy():\n    return 2.0\n"
    payload = json.dumps({
        "type": "AST_MUTATION",
        "target_file": DUMMY_FILE,
        "function_name": "calculate_exergy",
        "new_source": new_source
    })
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO cortex_swarm_queue (agent, payload, status, timestamp) VALUES (?, ?, 'pending', ?)",
        ("SAGE_COUNCIL", payload, time.time())
    )
    conn.commit()
    conn.close()

def run_test():
    setup()
    import dummy_exergy
    print(f"[PRE] Exergy: {dummy_exergy.calculate_exergy()} from {dummy_exergy.__file__}")
    
    print("[+] Injecting AST_MUTATION task into cortex_swarm_queue...")
    inject_task()
    
    daemon = OutboxDaemon()
    print("[+] Running OutboxDaemon.drain_once_sync()...")
    daemon.drain_once_sync()
    
    import importlib
    import time
    time.sleep(0.5) # Sleep to ensure mtime changes
    importlib.invalidate_caches()
    
    print(f"[DEBUG] dummy_exergy file before reload: {dummy_exergy.__file__}")
    print(f"[DEBUG] Function ID before reload: {id(dummy_exergy.calculate_exergy)}")
    with open(dummy_exergy.__file__, "r") as f:
        print(f"[DEBUG] File contents on disk: {repr(f.read())}")
    
    importlib.reload(dummy_exergy)
    print(f"[DEBUG] dummy_exergy file after reload: {dummy_exergy.__file__}")
    print(f"[DEBUG] Function ID after reload: {id(dummy_exergy.calculate_exergy)}")
    print(f"[DEBUG] Function constants after reload: {dummy_exergy.calculate_exergy.__code__.co_consts}")
    
    print(f"[POST] Exergy: {dummy_exergy.calculate_exergy()}")
    
    if dummy_exergy.calculate_exergy() == 2.0:
        print("[SUCCESS] C5-REAL AST Autopoiesis executed locally!")
    else:
        print("[FAILED] AST Autopoiesis did not execute.")

if __name__ == "__main__":
    run_test()
