#!/usr/bin/env python3
"""
Death Protocol - Thermodynamic Purge System for AI-generated code.
C5-REAL Execution.

Deterministic AST evaluation with 6 penalties:
1. LOC (Lines of code)
2. McCabe (Cyclomatic complexity)
3. Dead Code (Unused variables/functions)
4. Imports (Excessive/unused)
5. Depth (Nesting depth)
6. AI Slop (Generic naming, redundant comments, AI patterns)

Returns exit code 1 on grade F.
"""

import ast
import sys
import os

def _print(msg):
    sys.stdout.write(msg + "\n")

class DeathProtocolVisitor(ast.NodeVisitor):
    def __init__(self, source_code):
        self.source_code = source_code
        self.lines = source_code.split('\n')
        self.penalties = {
            'loc': 0,
            'mccabe': 0,
            'dead_code': 0,
            'imports': 0,
            'depth': 0,
            'ai_slop': 0
        }
        
        self.defined_names = set()
        self.used_names = set()
        self.imported_names = set()
        self.current_depth = 0
        
        self.analyze_loc()
        self.analyze_ai_slop_text()

    def analyze_loc(self):
        # Penalty for excessive lines of code
        loc = len([l for l in self.lines if l.strip() and not l.strip().startswith('#')])
        if loc > 300:
            self.penalties['loc'] += (loc - 300) // 25
            
    def analyze_ai_slop_text(self):
        # Penalty for AI boilerplate and excessive commenting
        ai_keywords = ['here is the code', 'as an ai', 'sure!', 'let me know', 'refactored version', '```python', 'snippet']
        for line in self.lines:
            if any(k in line.lower() for k in ai_keywords):
                self.penalties['ai_slop'] += 10
                
        # Excessive comments check (>30% of code)
        comments = len([l for l in self.lines if l.strip().startswith('#')])
        if len(self.lines) > 0 and (comments / len(self.lines)) > 0.3:
            self.penalties['ai_slop'] += int((comments / len(self.lines)) * 20)

    def visit(self, node):
        # Track nesting depth
        self.current_depth += 1
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.FunctionDef, ast.ClassDef)):
            if self.current_depth > 6:
                self.penalties['depth'] += (self.current_depth - 6) * 2
        super().visit(node)
        self.current_depth -= 1

    def visit_Import(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        self.penalties['imports'] += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        self.penalties['imports'] += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.defined_names.add(node.name)
        
        # Check McCabe (Cyclomatic Complexity) simplified
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.And, ast.Or, ast.ExceptHandler)):
                complexity += 1
        
        if complexity > 10:
            self.penalties['mccabe'] += (complexity - 10) * 2
            
        # Check AI Slop (Generic names)
        generic_names = ['do_something', 'process_data', 'handle_stuff', 'manager', 'helper', 'utils', 'foo', 'bar']
        if node.name.lower() in generic_names:
            self.penalties['ai_slop'] += 15
            
        self.generic_visit(node)
        
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)

    def finalize(self):
        # Dead code heuristic
        unused = (self.defined_names | self.imported_names) - self.used_names
        # Filter out typical exceptions and dunders
        unused = {n for n in unused if not (n.startswith('__') and n.endswith('__')) and n not in ('main', '_print')}
        self.penalties['dead_code'] += len(unused) * 3

def evaluate_file(filepath):
    if not filepath.endswith('.py'):
        return 0, {}
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
            
        tree = ast.parse(source)
        visitor = DeathProtocolVisitor(source)
        visitor.visit(tree)
        visitor.finalize()
        
        total_penalty = sum(visitor.penalties.values())
        return total_penalty, visitor.penalties
    except Exception as e:
        _print(f"Error parsing {filepath}: {e}")
        return 100, {'error': str(e)}

def main():
    if len(sys.argv) < 2:
        _print("Usage: python death_protocol.py <target_directory_or_file>")
        sys.exit(1)
        
    target = sys.argv[1]
    
    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, filenames in os.walk(target):
            # Ignore virtual envs and standard hidden directories
            if '.venv' in root or '.git' in root or '__pycache__' in root:
                continue
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
                    
    _print(f"=== DEATH PROTOCOL INITIATED ===")
    _print(f"Reality Level: C5-REAL")
    _print(f"Target: {target}")
    _print("-" * 50)
    
    failed = False
    
    for f in files:
        penalty, details = evaluate_file(f)
        if penalty == 0 and not details:
            continue
            
        # Threshold for Grade F
        if penalty >= 50:
            _print(f"[F] {f} - ENTROPY PENALTY: {penalty}")
            _print(f"    Vector Breakdown: {details}")
            failed = True
        elif penalty >= 25:
            _print(f"[C] {f} - ENTROPY PENALTY: {penalty} (Warning)")
        else:
            _print(f"[A] {f} - ENTROPY PENALTY: {penalty}")
            
    _print("-" * 50)
    if failed:
        _print("FATAL: Code entropy exceeds thermodynamic limits. Grade F detected.")
        _print("ACTION: Root entropy purge required.")
        sys.exit(1)
    else:
        _print("SUCCESS: Code entropy within acceptable bounds. Exergy preserved.")
        sys.exit(0)

if __name__ == "__main__":
    main()
