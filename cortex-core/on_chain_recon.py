import subprocess
import json
import os
import sys

# CORTEX On-Chain Recon v6.5 — Target Acquisition (Ω₆)
def get_live_target():
    """Fetches the latest contest repo from Code4rena."""
    print("📡 [RECON] Scanning Code4rena Repositories...")
    try:
        # Using gh CLI for authentic, high-speed recon
        cmd = ["gh", "repo", "list", "code-423n4", "--limit", "1", "--json", "name,url,description"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        repos = json.loads(result.stdout)
        
        if repos:
            target = repos[0]
            print(f"🎯 [RECON] Locked Target: {target['name']}")
            return target
        return None
    except Exception as e:
        print(f"❌ [RECON] Scan Failure: {e}")
        return None

if __name__ == "__main__":
    target = get_live_target()
    if target:
        # Save to current recon state
        with open("/tmp/cortex_recon_target.json", "w") as f:
            json.dump(target, f)
        print(f"✅ [RECON] Target Persisted: {target['url']}")
        
        # Trigger the X100 Fuzzer (C5-REAL)
        import requests
        try:
            r = requests.post("http://localhost:8000/trigger_fuzz", json={
                "url": target["url"],
                "effort": "ultrathink"
            })
            print(f"🚀 [C5-REAL] X100 Fuzzer Engaged: {r.status_code}")
        except:
            print("⚠️ [RECON] Fuzzer not active, target queued.")
