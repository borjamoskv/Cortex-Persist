# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: check-typing
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import json
import subprocess
import sys
import os

BASELINE_FILE = "typing_baseline.json"

def get_error_count(data):
    return data.get("summary", {}).get("errorCount", 0)

def main():
    if not os.path.exists(BASELINE_FILE):
        print(f"Baseline file {BASELINE_FILE} not found. Skipping strict baseline check.")
        baseline_errors = float('inf')
    else:
        with open(BASELINE_FILE, "r") as f:
            baseline_data = json.load(f)
        baseline_errors = get_error_count(baseline_data)

    print("Running pyright...")
    result = subprocess.run(["pyright", "--outputjson"], capture_output=True, text=True)
    
    try:
        current_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to parse pyright output.")
        print(result.stdout)
        sys.exit(1)

    current_errors = get_error_count(current_data)
    print(f"Current errors: {current_errors}")
    print(f"Baseline errors: {baseline_errors}")

    if current_errors > baseline_errors:
        print(f"\n[!] ERROR: Typing errors increased from {baseline_errors} to {current_errors}.")
        print("Please fix the new typing errors. Do not increase the technical debt.")
        sys.exit(1)
    elif current_errors < baseline_errors:
        print(f"\n[+] SUCCESS: Typing errors decreased! Consider updating {BASELINE_FILE} with: pyright --outputjson > {BASELINE_FILE}")
    else:
        print("\n[=] OK: Typing errors remained the same.")
        
    sys.exit(0)

if __name__ == "__main__":
    main()
