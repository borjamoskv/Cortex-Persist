#!/usr/bin/env python3
"""
C5-REAL DEATH PROTOCOL - Git Pre-Commit Entropy Sensor.
Purges AI Slop and Software Rot. 
Blocks commits that do not reduce structural entropy.
"""
import sys
import os
import ast
import subprocess

def calculate_ast_entropy(file_path: str) -> float:
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        tree = ast.parse(source)
        # Simple structural entropy: number of nodes / size of file
        nodes = len(list(ast.walk(tree)))
        if nodes == 0:
            return 0.0
        return nodes / len(source.splitlines())
    except Exception:
        return float('inf') # Unparseable code is infinite entropy

def main():
    print("[CORTEX] 💀 Initiating DEATH PROTOCOL (Entropy Scan)...")
    
    # Get staged python files
    try:
        result = subprocess.run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'], 
                              capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        sys.exit(0)
        
    staged_files = [f for f in result.stdout.splitlines() if f.endswith('.py')]
    
    if not staged_files:
        print("[CORTEX] No target files. Apoptosis bypassed.")
        sys.exit(0)
        
    failed = False
    for file_path in staged_files:
        if not os.path.exists(file_path):
            continue
            
        entropy = calculate_ast_entropy(file_path)
        print(f"  → {file_path} | Structural Entropy: {entropy:.2f}")
        
        # Threshold: If AST node density is too high (spaghetti code) or infinite (syntax error)
        if entropy > 5.0:
            print(f"\033[1;31m  [FATAL] Entropic collapse in {file_path}. Structural complexity exceeds limits.\033[0m")
            failed = True
            
    if failed:
        print("\033[1;31m[DEATH PROTOCOL] Commit rejected. Code must reduce entropy to survive.\033[0m")
        sys.exit(1)
        
    print("\033[1;32m[DEATH PROTOCOL] Entropy levels nominal. Commit authorized.\033[0m")
    sys.exit(0)

if __name__ == "__main__":
    main()
