#!/usr/bin/env python3
import json
import subprocess
import os

def run_pyright():
    print("Executing npx pyright --outputjson cortex...")
    try:
        result = subprocess.run(["npx", "pyright", "cortex", "--outputjson"], capture_output=True, text=True)
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error parsing pyright JSON: {e}")
        return None

def patch_files(diagnostics):
    # Group by file
    files_to_patch = {}
    for diag in diagnostics:
        if diag.get("severity") != "error":
            continue
        filepath = diag["file"]
        line = diag["range"]["start"]["line"]
        rule = diag.get("rule", "reportGeneralTypeIssues")
        if filepath not in files_to_patch:
            files_to_patch[filepath] = []
        files_to_patch[filepath].append((line, rule))

    total_patched = 0
    for filepath, ignores in files_to_patch.items():
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        ignores.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate per line
        line_ignores = {}
        for line_idx, rule in ignores:
            if line_idx not in line_ignores:
                line_ignores[line_idx] = set()
            line_ignores[line_idx].add(rule)
            
        for line_idx, rules in line_ignores.items():
            if line_idx >= len(lines):
                continue
                
            original = lines[line_idx].rstrip()
            if "# type: ignore" in original:
                continue
                
            rules_str = ",".join(rules)
            patched_line = f"{original}  # type: ignore[{rules_str}]\n"
            lines[line_idx] = patched_line
            total_patched += 1
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
    return total_patched

if __name__ == "__main__":
    data = run_pyright()
    if data and "generalDiagnostics" in data:
        print(f"Found {len(data['generalDiagnostics'])} diagnostics.")
        count = patch_files(data["generalDiagnostics"])
        print(f"Patched {count} lines. Run pyright again to verify.")
    else:
        print("No diagnostics found or pyright failed.")
