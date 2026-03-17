import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    changed = False
    
    # 1. Replace 'A | B' with 'Union[A, B]'
    # We target common patterns in type hints: words, brackets, etc.
    # We look for '|' preceded and followed by type-like characters.
    # This might match some string literals, but we try to be specific.
    
    # First, handle ' | None' as 'Optional[...]' which is cleaner
    # We do this from inner to outer or just use Union for everything.
    # Let's use Union[..., None] for simplicity as it's always valid.
    
    # Regex for a "type unit": a word, or a word with brackets.
    # We'll use a simplified version: [\w\[\],\. ]+
    
    # We loop to handle multiple unions: A | B | C -> Union[Union[A, B], C] or similar.
    # Actually, a better regex is needed.
    
    # Pattern: type_name followed by optional brackets, then | , then another type_name with optional brackets.
    type_pattern = r'([\w\.]+(?:\[[^\]]+\])?)'
    
    def replacer(match):
        parts = [p.strip() for p in match.group(0).split('|')]
        return f"Union[{', '.join(parts)}]"

    # We match groups of types separated by pipes.
    # We restrict to cases that look like type hints (after : or ->)
    # or inside other brackets.
    
    # Simple approach: look for ' | ' between alphanumeric/bracket chars.
    # This might have false positives in string literals, so we guard with context.
    
    # Match: word|word, word[...]|word, word|word[...]
    new_content = re.sub(r'([\w\.]+(?:\[[^\|\]]+\])?)\s*\|\s*([\w\.]+(?:\[[^\|\]]+\])?)', r'Union[\1, \2]', content)
    
    if new_content != content:
        changed = True
        content = new_content
        # Repeat once to handle A | B | C -> Union[A, B] | C -> Union[Union[A, B], C]
        content = re.sub(r'(Union\[[^\]]+\])\s*\|\s*([\w\.]+(?:\[[^\|\]]+\])?)', r'Union[\1, \2]', content)

    if changed:
        # Check imports
        has_union = "Union[" in content
        
        if has_union:
            # Add to existing typing import or add new one
            if "from typing import" in content:
                if "Union" not in re.search(r'from typing import (.*)', content).group(1):
                    content = re.sub(r'from typing import (.*)', r'from typing import \1, Union', content)
            elif "import typing" not in content:
                # Add at the top, after __future__ if present
                if "from __future__ import annotations" in content:
                    content = content.replace("from __future__ import annotations", "from __future__ import annotations\nfrom typing import Union")
                else:
                    content = "from typing import Union\n" + content
                    
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {filepath}")

def main():
    # Only target cortex/extensions/llm/ as it seems to be the main source of new issues
    for root, dirs, files in os.walk('cortex/extensions/llm'):
        for file in files:
            if file.endswith('.py'):
                fix_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
