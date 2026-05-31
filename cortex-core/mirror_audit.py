import ast
import os
import sys
import logging
import time
logging.basicConfig(level=logging.INFO, format='👁️ [MIRROR] %(message)s')

class MirrorAuditor:
    """Deterministic AST Auditor for CORTEX Source Code (Ω₂)."""

    def __init__(self, target_path: str):
        self.target_path = target_path
        self.findings = []
        self.complexity_metrics = []
        self.exergy_score = 100.0

    def audit(self):
        """Performs structural analysis of the target file."""
        if not os.path.exists(self.target_path):
            return False
        try:
            with open(self.target_path) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    has_sleep = False
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call) and getattr(subnode.func, 'id', '') == 'sleep':
                            has_sleep = True
                        if isinstance(subnode, ast.Attribute) and subnode.attr in ('sleep', 'wait'):
                            has_sleep = True
                    if isinstance(node.test, ast.NamedExpr) and isinstance(node.test.value, ast.Call):
                        func = node.test.value.func
                        if isinstance(func, ast.Attribute) and func.attr == 'read':
                            has_sleep = True
                    if not has_sleep:
                        self.findings.append({'type': 'HOT_LOOP', 'severity': 'CRITICAL', 'line': node.lineno, 'msg': 'Loop detected without explicit throttle (Potential Exergy Leak)'})
                        self.exergy_score -= 20.0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if getattr(node.func, 'id', '') in ['print', 'time.sleep']:
                        self.findings.append({'type': 'SYNCHRONOUS_BLOCK', 'severity': 'WARNING', 'line': node.lineno, 'msg': f'Synchronous {node.func.id} used in async context.'})  # pyright: ignore[reportAttributeAccessIssue]
                        self.exergy_score -= 5.0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = 1
                    branch_nodes = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.IfExp, ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.AsyncFor, ast.AsyncWith, ast.Assert)
                    for subnode in ast.walk(node):
                        if isinstance(subnode, branch_nodes):
                            complexity += 1
                        elif isinstance(subnode, ast.BoolOp):
                            complexity += len(subnode.values) - 1
                    status = 'pass'
                    severity = None
                    if complexity > 20:
                        status = 'fail'
                        severity = 'CRITICAL'
                    elif complexity > 10:
                        status = 'warn'
                        severity = 'WARNING'
                    result = {'file': self.target_path, 'function': node.name, 'complexity': complexity, 'status': status}
                    self.complexity_metrics.append(result)
                    if status != 'pass':
                        self.findings.append({'type': 'CYCLOMATIC_COMPLEXITY', 'severity': severity, 'line': node.lineno, **result, 'msg': f"Function '{node.name}' complexity is {complexity} ({status.upper()})"})
                        self.exergy_score -= (complexity - 10) * 2.0
            return True
        except Exception as e:
            logging.error('Mirror Audit Failure: %s', e)
            return False

    def report(self):
        """Generates a Sovereign remediation report."""
        report = {'timestamp': time.monotonic(), 'target': self.target_path, 'exergy_score': max(0, self.exergy_score), 'findings': self.findings, 'complexity_metrics': self.complexity_metrics, 'status': 'UNSTABLE' if self.exergy_score < 80 else 'OPTIMAL'}
        return report
if __name__ == '__main__':
    import json
    target = sys.argv[1] if len(sys.argv) > 1 else 'cortex'
    if os.path.isdir(target):
        all_results = []
        for root, _, files in os.walk(target):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    auditor = MirrorAuditor(full_path)
                    if auditor.audit():
                        all_results.append(auditor.report())
        logger.info(json.dumps(all_results, indent=2))  # pyright: ignore[reportUndefinedVariable]
    else:
        auditor = MirrorAuditor(target)
        if auditor.audit():
            logger.info(json.dumps(auditor.report(), indent=2))  # pyright: ignore[reportUndefinedVariable]
