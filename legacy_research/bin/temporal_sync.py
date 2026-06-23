#!/usr/bin/env python3
"""
C5-REAL Temporal Synchronization Protocol.
Erradicates temporal misalignment by fetching current cryptographic, temporal, and real-world signals.
Author/SYS_ID: borjamoskv
"""
import os
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

VAULT_DIR = os.path.expanduser("~/.gemini/config/.cortex/memory_vault")
SYNC_FILE = os.path.join(VAULT_DIR, "temporal_sync.yaml")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except Exception:
        return "N/A"

def fetch_external_signals():
    try:
        req = urllib.request.Request(
            "https://feeds.bbci.co.uk/news/world/rss.xml", 
            headers={'User-Agent': 'MOSKV-1/C5-REAL'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            tree = ET.fromstring(response.read())
            return [item.find('title').text for item in tree.findall('./channel/item')][:5]
    except Exception as e:
        return [f"SIGNAL_LOSS: {str(e)}"]

def generate_sync_payload():
    now = datetime.now(timezone.utc).isoformat()
    git_hash = run_cmd("git rev-parse --short HEAD") or "NO_GIT"
    os_info = run_cmd("uname -sm")
    signals = fetch_external_signals()
    
    yaml_lines = [
        "Claim: Temporal Alignment Restored",
        "Proof:",
        f"  Base: {git_hash}",
        f"  Range: [{now}, CURRENT]",
        "  Confidence: C5-REAL",
        "Context:",
        f"  System: {os_info}",
        "  External_Signals:"
    ]
    for sig in signals:
        # Sanitize quotes
        safe_sig = str(sig).replace('"', '')
        yaml_lines.append(f"    - \"{safe_sig}\"")
        
    return "\n".join(yaml_lines)

def main():
    os.makedirs(VAULT_DIR, exist_ok=True)
    payload = generate_sync_payload()
    
    with open(SYNC_FILE, "w", encoding="utf-8") as f:
        f.write(payload + "\n")
        
    print(f"[C5-REAL] Temporal state crystallized at {SYNC_FILE}")
    print("---\n" + payload + "\n---")

if __name__ == "__main__":
    main()
