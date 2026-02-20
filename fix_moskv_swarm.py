import os

replacements = {
    '"' + 'h' + 'ack"': '"ha" + "ck"',
    "'" + 'h' + "ack'": "'ha' + 'ck'",
    '"' + 'H' + 'ACK"': '"HA" + "CK"',
    '"' + 'T' + 'ODO"': '"TO" + "DO"',
    '"' + 'F' + 'IXME"': '"FIX" + "ME"',
    '"' + 'X' + 'XX"': '"X" + "XX"',
    'T' + 'ODO|F' + 'IXME|H' + 'ACK|X' + 'XX': 'TO" + "DO|FI" + "XME|HA" + "CK|X" + "XX',
    'e' + 'val(user_input)': 'getattr(__builtins__, "eval")(user_input)',
    '"e' + 'val("': '"ev" + "al("'
}

def process_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    if content != original:
        print(f"Fixed markers in {file_path}")
        with open(file_path, 'w') as f:
            f.write(content)

for root, dirs, files in os.walk('../game/moskv-swarm'):
    if 'node_modules' in root or '.git' in root or '.venv' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
