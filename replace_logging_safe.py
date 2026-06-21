import os

import_stmt = "from cortex.observability.jsonl_logger import setup_cortex_logging\n"
replace_stmt = "setup_cortex_logging()"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    idx = content.find("logging.basicConfig(")
    if idx == -1:
        return

    modified = False
    new_content = ""
    start = 0

    while idx != -1:
        # Find matching parenthesis
        paren_count = 0
        end_idx = -1
        in_string = False
        string_char = None
        escape = False

        for i in range(idx + len("logging.basicConfig("), len(content)):
            char = content[i]
            
            if escape:
                escape = False
                continue
            
            if char == '\\':
                escape = True
                continue
                
            if char in ("'", '"'):
                # Check for triple quotes
                is_triple = False
                if i + 2 < len(content) and content[i:i+3] == char * 3:
                    is_triple = True
                    
                if not in_string:
                    in_string = True
                    string_char = char * 3 if is_triple else char
                elif in_string and string_char == (char * 3 if is_triple else char):
                    in_string = False
                    string_char = None
                    if is_triple:
                        i += 2
                continue

            if not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    if paren_count == 0:
                        end_idx = i
                        break
                    else:
                        paren_count -= 1
        
        if end_idx != -1:
            new_content += content[start:idx] + replace_stmt
            start = end_idx + 1
            modified = True
        else:
            new_content += content[start:idx + 1]
            start = idx + 1
            
        idx = content.find("logging.basicConfig(", start)

    new_content += content[start:]

    if modified:
        if "setup_cortex_logging" not in new_content:
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
        if file.endswith('.py') and file != 'replace_logging_safe.py' and file != 'replace_logging.py':
            process_file(os.path.join(root, file))

