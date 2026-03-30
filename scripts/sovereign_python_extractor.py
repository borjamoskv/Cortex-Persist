"""CORTEX Sovereign — Python Structural Extractor.

Extracts classes, methods, docstrings, and CORTEX-specific 'Critical Paths'
using deterministic AST analysis. No external APIs required.
"""

import ast
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.tree import Tree
except ImportError:
    # Fallback if rich is not installed (though it should be in CORTEX)
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    class Table:
        def __init__(self, *args, **kwargs): pass
        def add_column(self, *args, **kwargs): pass
        def add_row(self, *args, **kwargs): pass
    class Panel:
        @staticmethod
        def fit(content, title=None): return content
    class Tree:
        def __init__(self, *args, **kwargs): pass
        def add(self, *args, **kwargs): return Tree("")

console = Console()

class SovereignExtractor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[str] = []
        self.critical_calls: List[Dict[str, Any]] = []
        self.sovereign_markers: List[str] = []
        self.current_class: Optional[str] = None

    def analyze(self, code: str):
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            console.print(f"[bold red]Syntax Error in {self.filename}:[/] {e}")

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
            if "cortex" in alias.name or "ledger" in alias.name:
                self.sovereign_markers.append(f"Import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
            if "cortex" in node.module or "ledger" in node.module:
                self.sovereign_markers.append(f"From {node.module} import ...")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name
        methods = []
        
        class_info = {
            "name": node.name,
            "lineno": node.lineno,
            "docstring": ast.get_docstring(node),
            "methods": methods
        }
        self.classes.append(class_info)
        
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_info = {
            "name": node.name,
            "lineno": node.lineno,
            "docstring": ast.get_docstring(node),
            "args": [arg.arg for arg in node.args.args],
            "returns": ast.unparse(node.returns) if node.returns else None
        }
        
        if self.current_class:
            # Find the class in self.classes and add this method
            for c in self.classes:
                if c["name"] == self.current_class:
                    c["methods"].append(func_info)
                    break
        else:
            self.functions.append(func_info)
            
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node) # Treat async as regular for metadata

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
        critical_keywords = {"ledger", "guard", "verify", "commit", "crypto", "asyncio", "playwright"}
        if any(kw in func_name.lower() for kw in critical_keywords):
            self.critical_calls.append({
                "name": func_name,
                "lineno": node.lineno,
                "context": self.current_class or "Global"
            })
            
        self.generic_visit(node)

    def report(self):
        console.print(Panel.fit(f"[bold blue]SOVEREIGN EXTRACTOR REPORT:[/] {self.filename}", title="CORTEX v8"))
        
        # Summary Tree
        root = Tree(f"[bold green]{self.filename}[/]")
        
        if self.classes:
            class_node = root.add("[bold cyan]Classes[/]")
            for c in self.classes:
                c_item = class_node.add(f"[yellow]{c['name']}[/] (L{c['lineno']})")
                if c['methods']:
                    for m in c['methods']:
                        c_item.add(f"[white]{m['name']}[/]")
        
        if self.functions:
            func_node = root.add("[bold cyan]Global Functions[/]")
            for f in self.functions:
                func_node.add(f"[yellow]{f['name']}[/] (L{f['lineno']})")
                
        console.print(root)
        
        # Critical Paths Table
        if self.critical_calls:
            table = Table(title="Critical Path Detection", show_header=True, header_style="bold magenta")
            table.add_column("Function", style="dim")
            table.add_column("Line", justify="right")
            table.add_column("Context")
            
            for call in self.critical_calls:
                table.add_row(call['name'], str(call['lineno']), call['context'])
            
            console.print(table)
        
        if self.sovereign_markers:
            console.print("\n[bold green]Sovereign Markers Found:[/]")
            for marker in self.sovereign_markers:
                console.print(f"  [+] {marker}")

def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: python sovereign_extractor.py <filename.py>[/]")
        sys.exit(1)
        
    path = sys.argv[1]
    if not os.path.exists(path):
        console.print(f"[red]Error: File {path} not found.[/]")
        sys.exit(1)
        
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
        
    extractor = SovereignExtractor(path)
    extractor.analyze(code)
    
    if "--json" in sys.argv:
        print(json.dumps({
            "filename": path,
            "classes": extractor.classes,
            "functions": extractor.functions,
            "critical_calls": extractor.critical_calls,
            "markers": extractor.sovereign_markers
        }, indent=2))
    else:
        extractor.report()

if __name__ == "__main__":
    main()
