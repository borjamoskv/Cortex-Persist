import subprocess
import time
import random
import os
import json
import glob
import sys
import threading
from typing import Dict

print(r"""
   ______ ____  ____  ________  __
  / ____// __ \/ __ \/_  __/ / / /
 / /    / / / / /_/ / / / / /_/ / 
/ /___ / /_/ / _, _/ / / / __  /  
\____/ \____/_/ |_| /_/ /_/ /_/   
CHAOS HARNESS (EL VERDUGO) v1.0
""")

# Clear previous physical state
if os.path.exists("ledger.jsonl"):
    os.remove("ledger.jsonl")
for f in glob.glob("snapshots/snap_*.json"):
    os.remove(f)

# Global Truth Topology
hash_history: Dict[int, str] = {0: "a97c91c23baf4e04ef640c2a413b4c828102931a62948feb86ab31b4ab6bbab6"} # v0 hash
metrics = {
    "total_kills": 0,
    "total_recoveries": 0,
    "divergences": 0,
    "corruptions_injected": 0,
    "last_known_version": 0
}

def stream_reader(process):
    """Reads stdout from the runner without blocking, tracks physics."""
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        try:
            data = json.loads(line.strip())
            v = data.get("version")
            h = data.get("state_hash")
            
            if data["type"] == "STATE_METRIC":
                hash_history[v] = h
                metrics["last_known_version"] = v
                sys.stdout.write(f"\r[LIVE] Causal Tick: {v} | Hash: {h[:8]}...")
                sys.stdout.flush()
                
            elif data["type"] == "RECOVERY_METRIC":
                print(f"\n[+] RECOVERY SUCCESS! Replay: {data['replay_duration_ms']}ms | Ver: {v}")
                if v in hash_history:
                    if hash_history[v] != h:
                        print(f"[!] DIVERGENCE DETECTED at Version {v}")
                        print(f"    Expected: {hash_history[v]}")
                        print(f"    Got:      {h}")
                        metrics["divergences"] += 1
                    else:
                        print(f"[✓] Causal Equivalence Verified for Version {v}")
                else:
                    print(f"[?] Unknown version {v} recovered (Timeline truncated beyond memory)")
                    hash_history[v] = h
                metrics["total_recoveries"] += 1
                
        except json.JSONDecodeError:
            pass

def inject_chaos():
    """Corrupts the physical medium."""
    if random.random() < 0.5:
        # Corrupt Snapshot
        snaps = glob.glob("snapshots/snap_*.json")
        if snaps:
            target = random.choice(snaps)
            print(f"\n[CHAOS] Corrupting Snapshot: {target}")
            with open(target, 'w') as f:
                f.write("{corrupted_json: fatal_error")
            metrics["corruptions_injected"] += 1
    else:
        # Truncate Ledger (Remove last line)
        if os.path.exists("ledger.jsonl"):
            with open("ledger.jsonl", 'r') as f:
                lines = f.readlines()
            if lines:
                print(f"\n[CHAOS] Amputating Ledger (Dropping causality)")
                with open("ledger.jsonl", 'w') as f:
                    f.writelines(lines[:-2]) # Drop last 2 events
                metrics["corruptions_injected"] += 1

TOTAL_DURATION = 15 # Run for 15 seconds for demonstration
start_time = time.time()

while time.time() - start_time < TOTAL_DURATION:
    process = subprocess.Popen(
        ["python", "cortex_live_runner.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    t_reader = threading.Thread(target=stream_reader, args=(process,))
    t_reader.daemon = True
    t_reader.start()
    
    # Let reality evolve for 1-3 seconds
    time.sleep(random.uniform(1.0, 3.0))
    
    # Unleash Hell
    print(f"\n[EXECUTIONER] Sending SIGKILL (-9) to PID {process.pid}")
    process.kill()
    process.wait()
    metrics["total_kills"] += 1
    
    inject_chaos()
    time.sleep(0.5)

print("\n\n--- CHAOS HARNESS RESULTS ---")
print(f"Total Uptime:        {TOTAL_DURATION}s")
print(f"Process Kills:       {metrics['total_kills']}")
print(f"Corruptions:         {metrics['corruptions_injected']}")
print(f"Successful Reboots:  {metrics['total_recoveries']}")
print(f"Causal Divergences:  {metrics['divergences']}")
print(f"Peak Version:        {metrics['last_known_version']}")

if metrics["divergences"] > 0:
    print("\n[FAILED] CORTEX failed to preserve timeline integrity.")
    sys.exit(1)
else:
    print("\n[VERIFIED] CORTEX is immortal. Replay Equivalence Holds.")
    sys.exit(0)
