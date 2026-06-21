import ast
import re

class CodeParser:
    # ---------- PYTHON (AST REAL) ----------
    def parse_python(self, code: str):
        result = {"classes": [], "functions": [], "imports": []}
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return result

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result["classes"].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                result["functions"].append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                result["functions"].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                result["imports"].append(module)
        return result

    # ---------- JS / TS (REGEX LIGERO) ----------
    def parse_js(self, code: str):
        result = {"classes": [], "functions": [], "imports": []}
        result["imports"] = re.findall(r'import\s+.*?from\s+[\'"](.+?)[\'"]', code)
        result["imports"] += re.findall(r'require\([\'"](.+?)[\'"]\)', code)
        result["functions"] += re.findall(r'function\s+([A-Za-z0-9_]+)', code)
        result["functions"] += re.findall(r'const\s+([A-Za-z0-9_]+)\s*=\s*\(', code)
        result["classes"] += re.findall(r'class\s+([A-Za-z0-9_]+)', code)
        return result
