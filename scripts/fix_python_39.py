import ast
import os
import sys

def get_union_str(node):
    def collect(n):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            collect(n.left)
            collect(n.right)
        else:
            parts.append(ast.unparse(n))
    parts = []
    collect(node)
    if "None" in parts:
        others = [p for p in parts if p != "None"]
        if not others: return "None"
        if len(others) == 1: return f"Optional[{others[0]}]"
        return f"Optional[Union[{', '.join(others)}]]"
    return f"Union[{', '.join(parts)}]"

def fix_file(path):
    try:
        with open(path, "r") as f: source = f.read()
    except: return False
    try: tree = ast.parse(source)
    except: return False

    replacements = []
    needed_typing = set()

    def process_annotation(node):
        # Walk the subtree to find ALL BinOps with BitOr
        for child in ast.walk(node):
            if isinstance(child, ast.BinOp) and isinstance(child.op, ast.BitOr):
                # Only take the top-most BinOp in a chain
                # (ast.walk visits parent before children, so if we find it, 
                # we should skip its children in the next steps? 
                # Actually, if we use a list of replaced nodes, we can avoid duplicates.)
                pass

    # Better approach: find all BinOps, check if they are inside an annotation
    all_binops = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            all_binops.append(node)
    
    # We only care about BinOps that are part of an annotation
    # To find if a node is in an annotation, we can check parents, but AST doesn't have them.
    # Instead, let's use a Visitor to mark nodes.
    
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def is_in_annotation(node):
        curr = node
        while curr in parents:
            p = parents[curr]
            if isinstance(p, ast.arg) and p.annotation == curr: return True
            if isinstance(p, ast.AnnAssign) and p.annotation == curr: return True
            if isinstance(p, ast.FunctionDef) and p.returns == curr: return True
            if isinstance(p, (ast.AsyncFunctionDef)) and p.returns == curr: return True
            curr = p
        return False

    annotation_binops = [b for b in all_binops if is_in_annotation(b)]
    if not annotation_binops: return False

    # Filter to only keep top-most BinOps
    top_binops = []
    for b in annotation_binops:
        is_top = True
        # If parent is also a BitOr BinOp, then this one isn't top-most
        if b in parents:
            p = parents[b]
            if isinstance(p, ast.BinOp) and isinstance(p.op, ast.BitOr):
                is_top = False
        if is_top:
            top_binops.append(b)

    for b in top_binops:
        new_text = get_union_str(b)
        replacements.append((b.lineno, b.col_offset, 
                             getattr(b, "end_lineno", b.lineno),
                             getattr(b, "end_col_offset", b.col_offset),
                             new_text))
        if "Union[" in new_text: needed_typing.add("Union")
        if "Optional[" in new_text: needed_typing.add("Optional")

    # Typing imports
    existing_typing = set()
    typing_import_line = -1
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            if typing_import_line == -1:
                typing_import_line = node.lineno
                existing_typing.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "typing" and typing_import_line == -1:
                    existing_typing.add("typing"); typing_import_line = node.lineno

    replacements.sort(key=lambda x: (x[0], x[1]), reverse=True)
    lines = source.splitlines(keepends=True)
    for sl, sc, el, ec, nt in replacements:
        if sl == el: lines[sl-1] = lines[sl-1][:sc] + nt + lines[sl-1][ec:]
        else:
            lines[sl-1] = lines[sl-1][:sc] + nt + lines[el-1][ec:]
            del lines[sl : el]

    to_add = needed_typing - existing_typing
    if to_add:
        if typing_import_line != -1:
            all_imports = ", ".join(sorted(existing_typing | to_add))
            lines[typing_import_line-1] = f"from typing import {all_imports}\n"
        else:
            future_line = -1
            for i, line in enumerate(lines):
                if "from __future__ import annotations" in line:
                    future_line = i; break
            import_all = ", ".join(sorted(to_add))
            if future_line != -1: lines.insert(future_line + 1, f"from typing import {import_all}\n")
            else: lines.insert(0, f"from typing import {import_all}\n")

    with open(path, "w") as f: f.write("".join(lines))
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    target = sys.argv[1]
    if os.path.isfile(target): fix_file(target)
    else:
        for root, dirs, files in os.walk(target):
            for f in files:
                if f.endswith(".py"): fix_file(os.path.join(root, f))
