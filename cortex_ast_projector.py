import ast
import argparse
import sys
import os
import asyncio
import aiosqlite
from pathlib import Path

class ASTProjector(ast.NodeTransformer):
    """
    Acts as the Maxwell's Demon for the Context Window.
    Prunes high-entropy (irrelevant) function bodies while keeping structural signatures intact.
    """
    def __init__(self, target_nodes):
        self.target_nodes = set(target_nodes)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name not in self.target_nodes:
            docstring = ast.get_docstring(node)
            if docstring:
                node.body = [ast.Expr(value=ast.Constant(value=docstring))]
            else:
                node.body = [ast.Pass()]
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        if node.name not in self.target_nodes:
            docstring = ast.get_docstring(node)
            if docstring:
                node.body = [ast.Expr(value=ast.Constant(value=docstring))]
            else:
                node.body = [ast.Pass()]
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return node

def project_ast(source_code, target_nodes):
    from cortex.engine.ast_validator import enforce_strict_types
    enforce_strict_types(source_code, filename="<ast_projector>")
    tree = ast.parse(source_code)
    projector = ASTProjector(target_nodes)
    projected_tree = projector.visit(tree)
    ast.fix_missing_locations(projected_tree)
    return ast.unparse(projected_tree)

def calculate_exergy_metrics(original_code, projected_code):
    orig_tokens = max(len(original_code) / 4, 1)
    proj_tokens = max(len(projected_code) / 4, 1)
    reduction = ((orig_tokens - proj_tokens) / orig_tokens) * 100
    e_info_orig = 1 / orig_tokens
    e_info_proj = 1 / proj_tokens
    multiplier = e_info_proj / e_info_orig
    return orig_tokens, proj_tokens, reduction, multiplier

async def fetch_fact_content(fact_id: int, db_path: str) -> str:
    # Phase 3 Synthesis: AST Projector consults the EDG (SQLite)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT content FROM facts WHERE id = ? AND is_tombstoned = 0", (fact_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                print(f"Error: Fact {fact_id} not found or tombstoned in EDG.")
                sys.exit(1)
            return row[0]

async def main():
    parser = argparse.ArgumentParser(description="[C5-REAL] AST Projector - Phase 3 Synthesis")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Source Python file")
    group.add_argument("--fact-id", type=int, help="Fact ID to extract from the EDG (SQLite)")
    parser.add_argument("--db-path", default="test.db", help="Path to SQLite EDG ledger")
    parser.add_argument("--targets", nargs="*", default=[], help="Target function/method names to preserve")
    args = parser.parse_args()

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: {filepath} not found.")
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        source_label = f"FILE: {args.file}"
    else:
        source = await fetch_fact_content(args.fact_id, args.db_path)
        source_label = f"EDG_FACT: {args.fact_id}"

    projected = project_ast(source, args.targets)
    orig_t, proj_t, red, mult = calculate_exergy_metrics(source, projected)

    print(f"=== [C5-REAL] AST PROJECTION PHASE 3: {source_label} ===")
    print(projected)
    print("\n=== THERMODYNAMIC METRICS: EXERGÍA INFORMACIONAL ===")
    print(f"Target Nodes Preserved: {args.targets if args.targets else 'None (Full Prune)'}")
    print(f"Original Tokens (approx): {orig_t:.0f}")
    print(f"Projected Tokens (approx): {proj_t:.0f}")
    print(f"Context Reduction (Entropy Purged): {red:.2f}%")
    print(f"E_info(C) Multiplier: {mult:.2f}x (Verifiable work per token)")

if __name__ == "__main__":
    asyncio.run(main())
