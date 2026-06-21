import os
import re

import_stmt = "from cortex.observability.jsonl_logger import setup_cortex_logging\n"
replace_stmt = "setup_cortex_logging()"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to match logging.basicConfig(...) spanning multiple lines
    pattern = re.compile(r'logging\.basicConfig\s*\([^)]*\)', re.DOTALL)
    
    if not pattern.search(content):
        return

    # Replace logging.basicConfig(...)
    new_content = pattern.sub(replace_stmt, content)

    # Add import if not present
    if "setup_cortex_logging" not in content:
        # Find the last import
        imports_end = 0
        lines = new_content.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                imports_end = i
        
        lines.insert(imports_end + 1, import_stmt)
        new_content = "".join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {filepath}")

for root, dirs, files in os.walk('.'):
    if '.venv' in root or '.git' in root or 'docs' in root:
        continue
    for file in files:
        if file.endswith('.py') and file != 'replace_logging.py':
            process_file(os.path.join(root, file))

