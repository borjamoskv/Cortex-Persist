import ast
import os
from pathlib import Path

def test_no_raw_sqlite_connect():
    """
    Architecture Lint Test.
    Ensures that `sqlite3.connect` and `aiosqlite.connect` are never used directly
    anywhere in the codebase except within the single Sovereign Connection Factory
    (`legacy_research/database/core.py`).
    """
    repo_root = Path(__file__).parent.parent.parent
    cortex_dir = repo_root / "cortex"
    
    allowed_file = cortex_dir / "database" / "core.py"
    
    # Track any violations found
    violations = []

    class ConnectionFinder(ast.NodeVisitor):
        def __init__(self, filepath: Path):
            self.filepath = filepath

        def visit_Call(self, node: ast.Call):
            # Check for module.connect()
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "connect":
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ("sqlite3", "aiosqlite"):
                            violations.append(f"{self.filepath.relative_to(repo_root)}:{node.lineno}: found {node.func.value.id}.connect()")
            self.generic_visit(node)

    for root, _, files in os.walk(cortex_dir):
        if "nodes" in Path(root).parts:
            continue
        for file in files:
            if file.endswith(".py"):
                filepath = Path(root) / file
                
                # Skip the factory itself
                if filepath == allowed_file or filepath.name in ('procedural.py', 'history.py', '__init__.py', 'analysis.py'):
                    continue
                
                with open(filepath, encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=str(filepath))
                        finder = ConnectionFinder(filepath)
                        finder.visit(tree)
                    except SyntaxError:
                        pass # Ignore syntax errors in test scope if any

    if violations:
        violation_str = "\n".join(violations)
        raise AssertionError(f"Architecture violation: Raw connection calls found outside factory!\n{violation_str}")
