import os
import re
from pathlib import Path

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace from cortex. with from babylon60.
    # Replace import cortex. with import babylon60.
    new_content = re.sub(r'\bfrom cortex\.', 'from babylon60.', content)
    new_content = re.sub(r'\bimport cortex\.', 'import babylon60.', new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

def main():
    dirs = ['babylon60/ledger', 'babylon60/guards', 'babylon60/crypto', 'babylon60/audit', 'babylon60/migrations']
    for d in dirs:
        p = Path(d)
        if not p.exists():
            continue
        for root, _, files in os.walk(p):
            for file in files:
                if file.endswith('.py'):
                    process_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
