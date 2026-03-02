import ast
import os
from pathlib import Path
from typing import Dict, List, Optional


class LandauerAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 0
        self.stats = {
            "functions": 0,
            "classes": 0,
            "decisions": 0,
        }
        self.node_metrics: List[Dict] = []
        self._current_node_stack: List[Dict] = []

    def _visit_node(self, node, key=None):
        if key:
            self.stats[key] += 1
        self.complexity += 1

        # Track complexity for the current stack of nodes (Func/Class)
        # All parents in the stack inherit the complexity of their sub-nodes
        for item in self._current_node_stack:
            item["complexity"] += 1

        self.generic_visit(node)

    def _push_node(self, node, node_type):
        node_info = {
            "name": getattr(node, "name", "<anonymous>"),
            "type": node_type,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "complexity": 1  # Base complexity
        }
        self._current_node_stack.append(node_info)

    def _pop_node(self):
        if self._current_node_stack:
            self.node_metrics.append(self._current_node_stack.pop())

    def visit_FunctionDef(self, node):
        self._push_node(node, "function")
        self._visit_node(node, "functions")
        self._pop_node()

    def visit_AsyncFunctionDef(self, node):
        self._push_node(node, "async_function")
        self._visit_node(node, "functions")
        self._pop_node()

    def visit_ClassDef(self, node):
        self._push_node(node, "class")
        self._visit_node(node, "classes")
        self._pop_node()

    def visit_If(self, node):
        self._visit_node(node, "decisions")

    def visit_For(self, node):
        self._visit_node(node, "decisions")

    def visit_AsyncFor(self, node):
        self._visit_node(node, "decisions")

    def visit_While(self, node):
        self._visit_node(node, "decisions")

    def visit_ExceptHandler(self, node):
        self._visit_node(node, "decisions")

    def visit_BoolOp(self, node):
        # AND/OR operators increase branching paths
        for _ in range(len(node.values) - 1):
            self._visit_node(node, "decisions")

    def visit_Lambda(self, node):
        self._visit_node(node, "functions")

    def visit_ListComp(self, node):
        self._visit_node(node, "decisions")

    def visit_DictComp(self, node):
        self._visit_node(node, "decisions")

    def visit_SetComp(self, node):
        self._visit_node(node, "decisions")

    def visit_GeneratorExp(self, node):
        self._visit_node(node, "decisions")

    def visit_Try(self, node):
        self._visit_node(node)

    def visit_With(self, node):
        self._visit_node(node)

    def visit_AsyncWith(self, node):
        self._visit_node(node)


def calculate_calcification(file_path: Path) -> Optional[Dict]:
    """
    Calculate the Calcification Score (Ω₂-C) for a file.
    Formula: Calcification = (Complexity * LOC) / 100
    Higher score indicates a 'Thermal Parasite' or architectural bone.
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
        analyzer = LandauerAnalyzer()
        analyzer.visit(tree)

        loc = len(content.splitlines())
        # Landauer metric: Entropy displacement vs Reduction
        # High complexity in low LOC is 'dense' (good),
        # High complexity in high LOC is 'bloated' (calcified).
        calcification_score = (analyzer.complexity * loc) / 100

        # Calculate scores for individual nodes
        for node in analyzer.node_metrics:
            node_loc = node["end_line"] - node["start_line"] + 1
            node["score"] = round((node["complexity"] * node_loc) / 10, 2)
            node["is_parasite"] = node["score"] > 30  # Granular threshold is lower

        return {
            "file": str(file_path.name),
            "loc": loc,
            "complexity": analyzer.complexity,
            "score": round(calcification_score, 2),
            "is_parasite": calcification_score > 50,
            "nodes": sorted(analyzer.node_metrics, key=lambda x: x["score"], reverse=True)
        }
    except (OSError, SyntaxError):
        return None


def audit_calcification(directory: Path, limit: int = 10) -> List[Dict]:
    """Scan directory for calcified files."""
    results = []
    skip_dirs = {".venv", "venv", ".cortex", ".git", "__pycache__", "node_modules"}
    for root, dirs, files in os.walk(directory):
        # Skip directories in-place
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                res = calculate_calcification(Path(root) / file)
                if res:
                    results.append(res)

    # Sort by calcification score (descending)
    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
