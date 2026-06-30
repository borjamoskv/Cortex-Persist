import os
import re
from pathlib import Path


def process_file(filepath: Path) -> bool:
    content = filepath.read_text("utf-8")
    original_content = content
    
    # 1. cortex_hash_truncated
    # hashlib.sha256(X).hexdigest()[:N] -> cortex_hash_truncated(X, length=N)
    content = re.sub(
        r'hashlib\.sha256\((.*?)\)\.hexdigest\(\)\[:(\d+)\]',
        r'cortex_hash_truncated(\1, length=\2)',
        content
    )
    
    # 2. cortex_hash
    # hashlib.sha256(X).hexdigest() -> cortex_hash(X)
    content = re.sub(
        r'hashlib\.sha256\((.*?)\)\.hexdigest\(\)',
        r'cortex_hash(\1)',
        content
    )
    
    # 3. cortex_hash_raw
    # hashlib.sha256(X).digest() -> cortex_hash_raw(\1)
    content = re.sub(
        r'hashlib\.sha256\((.*?)\)\.digest\(\)',
        r'cortex_hash_raw(\1)',
        content
    )
    
    # Check what we need to import
    needs_hash = 'cortex_hash(' in content
    needs_trunc = 'cortex_hash_truncated(' in content
    needs_raw = 'cortex_hash_raw(' in content
    
    if content != original_content:
        # We made changes, add imports if not present
        imports_needed = []
        if needs_hash and 'cortex_hash' not in original_content:
            imports_needed.append('cortex_hash')
        if needs_trunc and 'cortex_hash_truncated' not in original_content:
            imports_needed.append('cortex_hash_truncated')
        if needs_raw and 'cortex_hash_raw' not in original_content:
            imports_needed.append('cortex_hash_raw')
            
        if imports_needed:
            # Add to the top after __future__ or module docstring
            import_str = f"from babylon60.crypto.hash_registry import {', '.join(imports_needed)}\n"
            
            # Simple heuristic: put it after the first chunk of imports or at line 10
            lines = content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    if 'future' not in line:
                        insert_idx = i
                        break
            
            if insert_idx > 0:
                lines.insert(insert_idx, import_str.strip())
            else:
                lines.insert(0, import_str.strip())
                
            content = '\n'.join(lines) + '\n'
            
        # Clean up empty hashlib imports if no longer used
        if 'hashlib.' not in content:
            content = re.sub(r'^import hashlib\n', '', content, flags=re.MULTILINE)
            
        filepath.write_text(content, "utf-8")
        return True
    return False

def main():
    base_dir = Path("babylon60")
    files_changed = 0
    for root, _, sorted_files in os.walk(base_dir):
        # Skip crypto itself to avoid circular imports or messing up the registry
        if "crypto" in root and "hash_registry.py" in sorted_files:
            continue
            
        for file in sorted_files:
            if file.endswith(".py"):
                filepath = Path(root) / file
                # Don't modify the registry or provider itself blindly
                if file in ("hash_registry.py", "provider.py"):
                    continue
                if process_file(filepath):
                    print(f"Refactored: {filepath}")
                    files_changed += 1
                    
    print(f"Total files refactored: {files_changed}")

if __name__ == "__main__":
    main()
