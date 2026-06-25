import os
import re

ROOT = os.path.abspath(".")
DIRS_TO_SCAN = ["cortex", "legacy_research", "tests", "scripts", "docs"]
FILES_TO_SCAN = ["pyproject.toml", "README.md", "README.es.md", "README.zh.md", "Makefile", ".gitignore", ".cursorrules", "pytest.ini"]

def process_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            return
    
    if "cortex" not in content and "cortex-persist" not in content and "Cortex" not in content:
        return
        
    new_content = content.replace("cortex", "cortex")
    new_content = new_content.replace("Cortex", "Cortex")
    new_content = new_content.replace("cortex-persist", "cortex-persist")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {path}")

for d in DIRS_TO_SCAN:
    dir_path = os.path.join(ROOT, d)
    if not os.path.exists(dir_path):
        continue
    for root, dirs, files in os.walk(dir_path):
        if "__pycache__" in root or ".pytest_cache" in root or "node_modules" in root:
            continue
        for file in files:
            if file.endswith(('.py', '.json', '.yaml', '.yml', '.md', '.toml', '.sh', '.ini')):
                process_file(os.path.join(root, file))

for f in FILES_TO_SCAN:
    process_file(os.path.join(ROOT, f))
