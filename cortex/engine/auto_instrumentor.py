import ast
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMNodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.target_lines: list[int] = []
        self.llm_patterns = re.compile(r'(agent|llm|generate|inference|chat|predict)', re.IGNORECASE)

    def visit_FunctionDef(self, node):
        if self._is_target(node):
            self.target_lines.append(node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if self._is_target(node):
            self.target_lines.append(node.lineno)
        self.generic_visit(node)

    def _is_target(self, node) -> bool:
        # Match by function name
        if self.llm_patterns.search(node.name):
            return True
        # Match by docstring
        docstring = ast.get_docstring(node)
        if docstring and self.llm_patterns.search(docstring):
            return True
        # Match by calls inside the body
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ('create', 'invoke', 'predict', 'generate', 'chat'):
                        return True
                elif isinstance(child.func, ast.Name):
                    if self.llm_patterns.search(child.func.id):
                        return True
        return False

def instrument_file(filepath: Path, dry_run: bool = False) -> int:
    """
    Parses the AST to find LLM/Agent functions and injects the CORTEX MTK/Trace decorator
    using coordinate-based string patching to preserve formatting and comments.
    """
    try:
        source_code = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"[!] Error reading {filepath}: {e}")
        return 0

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        logger.error(f"[!] Syntax error in {filepath}. Skipping.")
        return 0

    visitor = LLMNodeVisitor()
    visitor.visit(tree)

    if not visitor.target_lines:
        return 0

    lines = source_code.splitlines()
    
    if "from cortex_persist import cortex_instrument" in source_code or "@cortex_instrument" in source_code:
        logger.info(f"[-] {filepath} already instrumented.")
        return 0

    if dry_run:
        logger.info(f"[DRY RUN] Would inject CORTEX in {filepath} at lines: {visitor.target_lines}")
        return len(visitor.target_lines)

    for lineno in sorted(visitor.target_lines, reverse=True):
        idx = lineno - 1
        original_line = lines[idx]
        indent = len(original_line) - len(original_line.lstrip())
        decorator = (" " * indent) + "@cortex_instrument()"
        lines.insert(idx, decorator)

    import_stmt = "from cortex_persist import cortex_instrument"
    
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_idx = i + 1
            
    lines.insert(insert_idx, import_stmt)

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f"[+] Instrumented {filepath} ({len(visitor.target_lines)} hooks injected)")
    
    return len(visitor.target_lines)

def instrument_directory(directory: Path, dry_run: bool = False) -> tuple[int, int]:
    files_modified = 0
    hooks_injected = 0
    
    for py_file in directory.rglob("*.py"):
        if "node_modules" in py_file.parts or ".venv" in py_file.parts or py_file.name.startswith("test_"):
            continue
            
        hooks = instrument_file(py_file, dry_run)
        if hooks > 0:
            files_modified += 1
            hooks_injected += hooks
            
    return files_modified, hooks_injected
