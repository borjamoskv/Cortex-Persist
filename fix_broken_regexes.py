import re
import os

def fix_regex_content(content):
    # This function handles the specific "Union[A, B]" pattern found in regexes
    # and converts it back to (A|B). Note: It should be bracket-aware.
    
    def replacer(match):
        name = match.group(0)[:-1] # Remove the [
        start = match.start() + len(name) + 1
        count = 1
        pos = start
        while count > 0 and pos < len(content):
            if content[pos] == '[': count += 1
            elif content[pos] == ']': count -= 1
            pos += 1
        
        if count == 0:
            inner = content[start:pos-1].strip()
            # Split by top-level commas
            parts = []
            p_start = 0
            p_count = 0
            for i, char in enumerate(inner):
                if char == '[': p_count += 1
                elif char == ']': p_count -= 1
                elif char == ',' and p_count == 0:
                    parts.append(inner[p_start:i].strip())
                    p_start = i + 1
            parts.append(inner[p_start:].strip())
            
            # Recurse for nested ones
            fixed_parts = [fix_regex_content(p) for p in parts]
            return f"(?:{'|'.join(fixed_parts)})"
        return match.group(0)

    # We match "Union[" but NOT prefixed with a dot or something that looks like code
    # Actually, in these files, Union[ is ALWAYS wrong inside a string.
    new_content = re.sub(r'Union\[', replacer, content)
    # Also handle the trailing "| None" if fix_python_310.py added it
    new_content = new_content.replace(' | None', '')
    # Handle the weird \Union from my previous run if any
    new_content = new_content.replace('\\Union', '\\')
    return new_content

def fix_file(path):
    with open(path, 'r') as f:
        content = f.read()
    
    # We only want to fix strings inside re.compile
    # A simple way is to find re.compile(...) and apply fix to its content
    # But since Union[ is definitely wrong in these specific files, we can be broader.
    
    if "re.compile" not in content and "ENTITY_PATTERNS" not in content:
         return False

    new_content = fix_regex_content(content)
    
    if new_content != content:
        with open(path, 'w') as f:
            f.write(new_content)
        return True
    return False

def main():
    files_to_fix = [
        'cortex/graph/patterns.py',
        'cortex/extensions/alma/taste.py',
        'cortex/extensions/llm/_validation.py',
        'cortex/cli/prompt_cmds.py',
        'cortex/engine/storage_guard.py',
        'cortex/engine/membrane/sanitizer.py',
        'cortex/extensions/perception/base.py',
        'cortex/mcp/guard.py'
    ]
    for f in files_to_fix:
        path = os.path.join('.', f)
        if os.path.exists(path):
            if fix_file(path):
                print(f"Fixed regexes in: {path}")

if __name__ == "__main__":
    main()
