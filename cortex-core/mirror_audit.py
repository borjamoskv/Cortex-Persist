import ast
import os
import sys
import logging
import time

# CORTEX Mirror Protocol v6.2 — The Epistemic Auditor
logging.basicConfig(level=logging.INFO, format="👁️ [MIRROR] %(message)s")

class ComplexityVisitor(ast.NodeVisitor):
    """AST Visitor to calculate Cyclomatic Complexity."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_MatchCase(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Do not descend into nested functions
        pass

    def visit_AsyncFunctionDef(self, node):
        # Do not descend into nested functions
        pass

class MirrorAuditor:
    """Deterministic AST Auditor for CORTEX Source Code (Ω₂)."""

    def __init__(self, target_path: str):
        self.target_path = target_path
        self.findings = []
        self.exergy_score = 100.0

    def audit(self):
        """Performs structural analysis of the target file."""
        if not os.path.exists(self.target_path):
            return False
            
        try:
            with open(self.target_path) as f:
                tree = ast.parse(f.read())

            # 1. Hot Loop Analysis (Axiom Ω₆)
            for node in ast.walk(tree):
                if isinstance(node, ast.While) or isinstance(node, ast.For):
                    has_sleep = False
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call) and getattr(subnode.func, 'id', '') == 'sleep':
                             has_sleep = True
                        if isinstance(subnode, ast.Attribute) and subnode.attr == 'sleep':
                             has_sleep = True
                    
                    if not has_sleep:
                        self.findings.append({
                            "type": "HOT_LOOP",
                            "severity": "CRITICAL",
                            "line": node.lineno,
                            "msg": "Loop detected without explicit throttle (Potential Exergy Leak)"
                        })
                        self.exergy_score -= 20.0

            # 2. Blockage Detection
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if getattr(node.func, 'id', '') in ['print', 'time.sleep']:
                         self.findings.append({
                             "type": "SYNCHRONOUS_BLOCK",
                             "severity": "WARNING",
                             "line": node.lineno,
                             "msg": f"Synchronous {node.func.id} used in async context."
                         })
                         self.exergy_score -= 5.0

            # 3. Structural Complexity
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visitor = ComplexityVisitor()
                    # Visit only children of function definition to calculate complexity of this function
                    for body_node in node.body:
                        visitor.visit(body_node)

                    complexity = visitor.complexity
                    if complexity > 20:
                        self.findings.append({
                            "type": "CYCLOMATIC_COMPLEXITY",
                            "severity": "CRITICAL",
                            "line": node.lineno,
                            "function": node.name,
                            "complexity": complexity,
                            "status": "FAIL",
                            "msg": f"Function '{node.name}' complexity is {complexity} (Threshold: 20)"
                        })
                        self.exergy_score -= 20.0
                    elif complexity > 10:
                        self.findings.append({
                            "type": "CYCLOMATIC_COMPLEXITY",
                            "severity": "WARNING",
                            "line": node.lineno,
                            "function": node.name,
                            "complexity": complexity,
                            "status": "WARN",
                            "msg": f"Function '{node.name}' complexity is {complexity} (Threshold: 10)"
                        })
                        self.exergy_score -= 5.0

            return True
        except Exception as e:
            logging.error("Mirror Audit Failure: %s", e)
            return False

    def report(self):
        """Generates a Sovereign remediation report."""
        report = {
            "timestamp": time.time(),
            "target": self.target_path,
            "exergy_score": max(0, self.exergy_score),
            "findings": self.findings,
            "status": "UNSTABLE" if self.exergy_score < 80 else "OPTIMAL"
        }
        return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mirror_audit.py <target_file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    targets = []
    if os.path.isdir(target):
        for root, _, files in os.walk(target):
            for file in files:
                if file.endswith(".py"):
                    targets.append(os.path.join(root, file))
    else:
        targets.append(target)

    reports = []
    for t in targets:
        auditor = MirrorAuditor(t)
        if auditor.audit():
            reports.append(auditor.report())

    import json
    if len(reports) == 1 and not os.path.isdir(target):
        print(json.dumps(reports[0], indent=2))
    else:
        print(json.dumps(reports, indent=2))
