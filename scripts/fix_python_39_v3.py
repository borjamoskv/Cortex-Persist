import os
import re
import sys

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return

    changed = False
    
    # 1. Replace 'A | B' with 'Union[A, B]'
    # Handle multiple pipes A | B | C -> Union[A, Union[B, C]]
    # This regex is a bit greedy but should work for most type hints.
    # We look for words, brackets, and dots separated by '|'.
    
    original_content = content
    
    # Simple replacement for common case 'type | None' -> 'Optional[type]'
    content = re.sub(r'([\w\.]+(?:\[[^\]]+\])?)\s*\|\s*None', r'Optional[\1]', content)
    content = re.sub(r'None\s*\|\s*([\w\.]+(?:\[[^\]]+\])?)', r'Optional[\1]', content)
    
    # General replacement for 'A | B' -> 'Union[A, B]'
    # We repeat until no more pipes are found to handle A | B | C
    while ' | ' in content or '|' in content:
        # Match A | B where A and B are type-like
        new_content = re.sub(r'([\w\.]+(?:\[[^\|\]]+\])?)\s*\|\s*([\w\.]+(?:\[[^\|\]]+\])?)', r'Union[\1, \2]', content)
        if new_content == content:
            break
        content = new_content

    if content != original_content:
        changed = True
        
        # 2. Fix imports
        has_union = "Union[" in content
        has_optional = "Optional[" in content
        
        needed = []
        if has_union: needed.append("Union")
        if has_optional: needed.append("Optional")
        
        if needed:
            # Look for existing typing import
            typing_match = re.search(r'from typing import (.*)', content)
            if typing_match:
                existing_imports = [i.strip() for i in typing_match.group(1).split(',')]
                for n in needed:
                    if n not in existing_imports:
                        existing_imports.append(n)
                # Sort them for tidiness
                existing_imports.sort()
                new_import_line = f"from typing import {', '.join(existing_imports)}"
                content = re.sub(re.escape(typing_match.group(0)), new_import_line, content, count=1)
            else:
                # No typing import found, add one
                import_line = f"from typing import {', '.join(needed)}\n"
                if "from __future__ import annotations" in content:
                    content = re.sub(r'from __future__ import annotations', "from __future__ import annotations\n" + import_line, content, count=1)
                else:
                    content = import_line + content

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")

def main():
    target_dir = 'cortex'
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        
    print(f"Scanning {target_dir}...")
    for root, dirs, files in os.walk(target_dir):
        # Skip pycache and hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                fix_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
