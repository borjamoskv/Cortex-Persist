import os
import ast

def analyze_dir(d):
    bare = 0
    bound = 0
    total = 0
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r') as file:
                    try:
                        tree = ast.parse(file.read(), filename=path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ExceptHandler):
                                if isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                                    total += 1
                                    if node.name is None:
                                        bare += 1
                                    else:
                                        bound += 1
                    except Exception:
                        pass
    return bare, bound, total

for d in ['cortex/engine', 'cortex/memory', 'cortex/swarm']:
    bare, bound, total = analyze_dir(os.path.join('/Users/borjafernandezangulo/30_CORTEX', d))
    print(f"{d}: {bare} bare, {bound} bound, {total} total")
