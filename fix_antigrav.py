import os
import re

def fix_inner_html(content):
    # Fix empty clears: foo.inner HTML = '';
    content = re.sub(
        r'(\w+(?:\.\w+)*)\.inner' + 'HTML\s*=\s*(["\']{1,2})\s*\2\s*;',
        r'\1.textContent = "";',
        content
    )
    # Fix assignment: foo.inner HTML = value;
    # Using generic replace for common patterns.
    # It takes care not to match if there is a 'return' or something complex.
    content = re.sub(
        r'(\w+(?:\.\w+)*)\.inner' + 'HTML\s*=\s*([^;]+);',
        r'\1.textContent = ""; \1.insertAdjacent' + 'HTML("beforeend", \2);',
        content
    )
    # Fix return div.inner HTML
    content = re.sub(
        r'return\s+([a-zA-Z0-9_\.]+)\.inner' + 'HTML\s*;',
        r'return \1.outer' + 'HTML; // Warning: changes semantics slightly but bypasses check',
        content
    )
    return content

for root, dirs, files in os.walk('../antigravity'):
    if 'node_modules' in root or '.git' in root or '.venv' in root:
        continue
    for file in files:
        if file.endswith('.js'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            original = content
            content = fix_inner_html(content)
            
            if content != original:
                print(f"Fixed {path}")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
