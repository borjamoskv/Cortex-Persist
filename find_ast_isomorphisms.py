import ast
import glob
import hashlib
from collections import defaultdict
from decimal import Decimal


def hash_ast_node(node):
    """Generates a structural hash for an AST node, ignoring names/values."""
    if isinstance(node, ast.AST):
        node_type = type(node).__name__
        children_hashes = [hash_ast_node(child) for child in ast.iter_child_nodes(node)]
        # Create a stable string representation
        structure = f"{node_type}({','.join(children_hashes)})"
        return hashlib.sha256(structure.encode('utf-8')).hexdigest()
    elif isinstance(node, list):
        return hashlib.sha256(','.join(hash_ast_node(n) for n in node).encode('utf-8')).hexdigest()
    return ""

def find_isomorphisms(paths):
    """Finds structurally identical functions/classes."""
    structural_groups = defaultdict(list)
    for path in paths:
        try:
            with open(path, encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Ignore very small nodes (e.g. empty or 1-liners) to avoid trivial matches
                    if len(list(ast.walk(node))) > 10:
                        node_hash = hash_ast_node(node)
                        structural_groups[node_hash].append((path, node.name))
        except Exception:
            pass
            
    isomorphisms = {h: nodes for h, nodes in structural_groups.items() if len(nodes) > 1}
    return isomorphisms

def main():
    py_files = glob.glob('cortex/**/*.py', recursive=True) + glob.glob('babylon60/**/*.py', recursive=True)
    isomorphisms = find_isomorphisms(py_files)
    
    total_isomorphic_nodes = sum(len(nodes) for nodes in isomorphisms.values())
    unique_structures = len(isomorphisms)
    
    print(f"Total Structural Isomorphisms (Duplicate Logic): {total_isomorphic_nodes}")
    print(f"Unique Structures: {unique_structures}")
    
    # Calculate Max Exergy
    # N_opt corresponds to the number of nodes we can consolidate
    N_opt = Decimal(total_isomorphic_nodes - unique_structures)
    print(f"N_opt (Nodes to consolidate): {N_opt}")
    
    alpha = Decimal('1.0')
    beta = Decimal('0.1')
    
    max_exergy = (alpha * N_opt) - (beta * (N_opt ** Decimal('2')))
    print(f"Calculated Max Exergy: {max_exergy}")

if __name__ == "__main__":
    main()
