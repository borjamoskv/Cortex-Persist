#!/usr/bin/env python3
"""
[C5-REAL] Babylon 60 Batch Crystallizer Agent
Scans all conversations in the Antigravity brain and consolidates directives.
"""

import os
import json
import re
from pathlib import Path

def extract_all():
    home_dir = os.path.expanduser("~")
    brain_dir = Path(home_dir) / ".gemini" / "antigravity" / "brain"
    directives = set()
    print("[C5-REAL] Scanning all conversations for unconsolidated directives...")
    
    for d in brain_dir.iterdir():
        if d.is_dir():
            transcript = d / ".system_generated" / "logs" / "transcript.jsonl"
            if transcript.exists():
                with open(transcript, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if data.get("type") in ["PLANNER_RESPONSE", "USER_INPUT"]:
                                content = data.get("content", "")
                                matches = re.findall(r'(?:\[P[0-2]\]|Rule:|Directive:|MUST|NEVER)\s*(.*?)(?:\n|$)', content)
                                for match in matches:
                                    cleaned = match.strip()
                                    if len(cleaned) > 10:
                                        directives.add(cleaned)
                        except json.JSONDecodeError:
                            continue

    target_path = Path(home_dir) / "30_CORTEX" / "cortex_directives.yaml"
    print(f"[C5-REAL] Instrumenting {len(directives)} unique directives into {target_path}...")
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write("consolidated_session_directives:\n")
        for d in sorted(directives):
            # Escape inner quotes
            safe_d = d.replace('"', '\\"')
            f.write(f"  - rule: \"{safe_d}\"\n")
            
    print("[C5-REAL] Execution complete. Ready for Git Sentinel.")

if __name__ == "__main__":
    extract_all()
