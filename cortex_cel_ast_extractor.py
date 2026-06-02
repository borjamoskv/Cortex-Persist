import ast
import json
import os
import subprocess
from pathlib import Path

def get_git_info(filepath):
    try:
        authors = subprocess.check_output(
            ["git", "log", "--format=%an", filepath], text=True
        ).splitlines()
        unique_authors = len(set([a.strip() for a in authors if a.strip()]))
        
        commits = subprocess.check_output(
            ["git", "log", "--oneline", filepath], text=True
        ).splitlines()
        failures = sum(1 for c in commits if "fix" in c.lower() or "bug" in c.lower())
        
        return max(1, unique_authors), failures
    except Exception:
        return 1, 0

def extract_ast_features(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
        
    loc = len(content.splitlines())
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
        
    has_global_state = 0
    large_classes = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            has_global_state = 1
        elif isinstance(node, ast.ClassDef):
            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                if (node.end_lineno - node.lineno) > 200:
                    large_classes = 1
                    
    return {
        "loc": loc,
        "has_global_state": has_global_state,
        "has_large_classes": large_classes
    }

def main():
    print("Initiating C5-REAL AST Extraction...")
    dataset = []
    
    # Process only a subset of files to be fast and verifiable
    target_dirs = [Path("cortex-core"), Path("cortex_rs"), Path("api")]
    processed = 0
    
    for d in target_dirs:
        if not d.exists():
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if processed >= 100:
                    break
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    features = extract_ast_features(filepath)
                    if not features:
                        continue
                        
                    authors, failures = get_git_info(filepath)
                    
                    dataset.append({
                        "file": str(filepath),
                        "pattern_present": 1 if (features["has_global_state"] or features["has_large_classes"]) else 0,
                        "loc": features["loc"],
                        "authors": authors,
                        "failures": failures
                    })
                    processed += 1
            if processed >= 100:
                break
                
    with open(".cortex_ast_dataset.json", "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"C5-REAL: Extraídos {len(dataset)} archivos en .cortex_ast_dataset.json")

if __name__ == "__main__":
    main()
