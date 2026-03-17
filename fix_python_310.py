import os
import re

def replace_bracket_aware(name, replacement_fmt, content):
    def replacer(match):
        # find the balancing bracket for the one at match.start() + len(name)
        start = match.start() + len(name) + 1 # +1 for [
        count = 1
        pos = start
        while count > 0 and pos < len(content):
            if content[pos] == '[': count += 1
            elif content[pos] == ']': count -= 1
            pos += 1
        if count == 0:
            inner = content[start:pos-1].strip()
            # If it's Union, we need to split by comma but be careful with nested stuff
            if name == 'Union':
                # very simple comma split for now, but better would be bracket-aware
                # finding the top-level comma
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
                return " | ".join(parts)
            return replacement_fmt.format(inner)
        return match.group(0)

    # We use a pattern that matches the START of the expression
    pattern = re.compile(rf'\b{name}\[')
    new_content = ""
    last_pos = 0
    for match in pattern.finditer(content):
        new_content += content[last_pos:match.start()]
        # Find closing bracket
        start = match.start() + len(name) + 1
        count = 1
        pos = start
        while count > 0 and pos < len(content):
            if content[pos] == '[': count += 1
            elif content[pos] == ']': count -= 1
            pos += 1
        
        if count == 0:
            inner = content[start:pos-1].strip()
            if name == 'Optional':
                result = f"{inner} | None"
            elif name == 'Union':
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
                result = " | ".join(parts)
            else:
                result = match.group(0) # should not happen
            
            new_content += result
            last_pos = pos
        else:
            new_content += match.group(0)
            last_pos = match.end()
    
    new_content += content[last_pos:]
    return new_content

def fix_file(path):
    with open(path, 'r') as f:
        content = f.read()

    new_content = content
    # Run a few times for nested ones (e.g. A | B | None)
    for _ in range(3):
        new_content = replace_bracket_aware('Optional', "{} | None", new_content)
        new_content = replace_bracket_aware('Union', "{} | None", new_content)

    # Clean up imports
    lines = new_content.splitlines()
    new_lines = []
    for line in lines:
        if 'from typing import ' in line:
            # Remove Optional and Union from the import list
            # We need to be careful with commas
            parts = line.split('import')
            imports = [i.strip() for i in parts[1].split(',')]
            filtered = [i for i in imports if i not in ('Optional', 'Union')]
            if not filtered:
                continue # Skip line if all imports removed
            line = f"{parts[0]}import {', '.join(filtered)}"
        new_lines.append(line)
    
    new_content = '\n'.join(new_lines) + ('\n' if new_content.endswith('\n') else '')

    if new_content != content:
        with open(path, 'w') as f:
            f.write(new_content)
        return True
    return False

def main():
    modified_count = 0
    for root, dirs, files in os.walk('.'):
        if '.git' in dirs: dirs.remove('.git')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if fix_file(path):
                    print(f"Fixed: {path}")
                    modified_count += 1
    print(f"Total files modified: {modified_count}")

if __name__ == "__main__":
    main()
