# [C5-REAL] Exergy-Maximized
"""
cat_id: refactor-aiosqlite
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import re
from pathlib import Path


def refactor_file(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
        
        # If it doesn't contain aiosqlite.connect, skip
        if "aiosqlite.connect" not in content:
            return False
            
        # Replace async with aiosqlite.connect( with async with connect_async(
        # or aiosqlite.connect( with connect_async(
        new_content = re.sub(r'aiosqlite\.connect\(', 'connect_async(', content)
        
        # Add import if missing
        if "connect_async" in new_content and "from babylon60.database.core import connect_async" not in new_content:
            # Insert after the last import
            lines = new_content.splitlines()
            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    last_import_idx = i
            
            if last_import_idx != -1:
                lines.insert(last_import_idx + 1, "from babylon60.database.core import connect_async")
                new_content = "\n".join(lines) + "\n"
        
        # Write back
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error {path}: {e}")
        return False

def main():
    workspace = Path(__file__).parent.parent.resolve()
    target_dirs = [workspace / "scripts"]
    
    count = 0
    for d in target_dirs:
        for f in d.rglob("*.py"):
            if refactor_file(f):
                print(f"🟢 Refactored {f.relative_to(workspace)}")
                count += 1
                
    print(f"Total refactored: {count}")

if __name__ == "__main__":
    main()
