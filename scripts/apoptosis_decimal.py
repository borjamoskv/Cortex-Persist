import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    changed = False
    lines = content.split('\n')
    new_lines = []
    
    # Matching var_score: float or score: float
    for line in lines:
        if re.search(r'score:\s*float\b', line):
            new_lines.append(re.sub(r'score:\s*float\b', 'score: Decimal', line))
            changed = True
        else:
            new_lines.append(line)
            
    if changed:
        # Inject import if not exists
        if 'from decimal import Decimal' not in content:
            new_content = 'from decimal import Decimal\n' + '\n'.join(new_lines)
        else:
            new_content = '\n'.join(new_lines)
            
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Decimal Patched: {filepath}")

for root, _, files in os.walk('babylon60'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
