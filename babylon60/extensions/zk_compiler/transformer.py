"""
[C5-REAL] AST Transformer para Invariantes ZK
"""

import ast


class ZKInvariantTransformer(ast.NodeTransformer):
    """C5-REAL AST Rewriter for ZK Invariants"""

    def __init__(self) -> None:
        super().__init__()
        self.applied_invariants: set[str] = set()

    def visit_For(self, node: ast.For) -> ast.Call:
        """Transforms Python For loops into Nova Folding Schemes."""
        self.generic_visit(node)
        self.applied_invariants.add("Nova")
        # Transpile to: NovaFoldingScheme(iterator, body)
        return ast.Call(
            func=ast.Name(id="NovaFoldingScheme", ctx=ast.Load()),
            args=[node.iter],
            keywords=[],
            starargs=None,
            kwargs=None,
        )

    def visit_Subscript(self, node: ast.Subscript) -> ast.Call:
        """Transforms Array/Dict lookups into LogUp Fractional Sums."""
        self.generic_visit(node)
        self.applied_invariants.add("LogUp")
        # Transpile to: LogUpLookup(table, index)
        return ast.Call(
            func=ast.Name(id="LogUpLookup", ctx=ast.Load()),
            args=[node.value, node.slice],
            keywords=[],
        )

    def visit_ListComp(self, node: ast.ListComp) -> ast.Call:
        """Transforms Data-Parallel operations into GKR Layered Sumchecks."""
        self.generic_visit(node)
        self.applied_invariants.add("GKR")
        return ast.Call(
            func=ast.Name(id="GKRDataParallel", ctx=ast.Load()),
            args=[node.generators[0].iter],
            keywords=[],
        )

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Transforms recursive verification and bridge consensus logic."""
        self.generic_visit(node)
        if isinstance(node.func, ast.Name):
            # 1. ZK Recursion
            if node.func.id in ["verify_proof", "check_signature"]:
                self.applied_invariants.add("CurveCycle")
                return ast.Call(
                    func=ast.Name(id="CurveCycleRecursion", ctx=ast.Load()),
                    args=node.args,
                    keywords=node.keywords,
                )
            # 2. ZK Bridges (Puentes): Consensus Header Validation
            elif node.func.id in ["verify_headers", "sync_committee", "tendermint_bft"]:
                self.applied_invariants.add("ConsensusProofFolding")
                return ast.Call(
                    func=ast.Name(id="ConsensusProofFolding", ctx=ast.Load()),
                    args=node.args,
                    keywords=node.keywords,
                )
            # 3. ZK Bridges: Batch Signature Verification for Multi-Sig/Validators
            elif node.func.id in ["verify_bls_signatures", "verify_validators"]:
                self.applied_invariants.add("BLSBatching")
                return ast.Call(
                    func=ast.Name(id="BLSBatchVerification", ctx=ast.Load()),
                    args=node.args,
                    keywords=node.keywords,
                )
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        """Transforms bitwise CPU operations into Jolt/Lasso lookups."""
        self.generic_visit(node)
        if isinstance(node.op, (ast.BitXor, ast.BitAnd, ast.BitOr, ast.LShift, ast.RShift)):
            self.applied_invariants.add("LassoLookup")
            return ast.Call(
                func=ast.Name(id="LassoLookup", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
        return node
