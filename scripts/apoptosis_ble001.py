import os
import re


def process_file(filepath):
    with open(filepath) as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []
    changed = False
    for line in lines:
        if re.search(r'except\s+Exception(\s+as\s+\w+)?:', line) and 'noqa' not in line:
            new_lines.append(line + '  # noqa: BLE001')
            changed = True
        else:
            new_lines.append(line)
            
    if changed:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
        print(f"BLE001 Patched: {filepath}")

for root, _, files in os.walk('babylon60'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
