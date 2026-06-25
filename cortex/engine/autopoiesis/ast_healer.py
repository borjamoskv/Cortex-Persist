"""
C5-REAL AST Healer.
The cognitive core of Ouroboros L6: Parses, patches, and delegates hot-swaps.
"""

from __future__ import annotations

import ast
import logging
import re
import sys

from cortex.engine.autopoiesis.hot_swap import HotSwapper
from cortex.engine.autopoiesis.sandbox import SandboxValidator

logger = logging.getLogger(__name__)

class _HealingTransformer(ast.NodeTransformer):
    def __init__(self, function_name: str, class_name: str | None, patch_node: ast.stmt):
        self.function_name = function_name
        self.class_name = class_name
        self.patch_node = patch_node
        self.patched = False

    def visit_ClassDef(self, node: ast.ClassDef):
        if self.class_name and node.name == self.class_name:
            for i, child in enumerate(node.body):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == self.function_name:
                    node.body[i] = self.patch_node
                    self.patched = True
                    return node
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.class_name and node.name == self.function_name:
            self.patched = True
            return self.patch_node
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if not self.class_name and node.name == self.function_name:
            self.patched = True
            return self.patch_node
        self.generic_visit(node)
        return node


class ASTHealer:
    """Detects exceptions and self-heals by modifying AST."""

    @staticmethod
    def heal_exception(
        exc: Exception, 
        module_name: str, 
        function_name: str, 
        patch_code: str, 
        class_name: str | None = None,
        test_path: str | None = None
    ) -> bool:
        """
        Attempts to heal the function that threw `exc`.
        `patch_code` should be a valid block of python code representing the new function definition.
        """
        logger.warning("Initiating Autopoietic Healing Protocol for %s:%s.%s", module_name, class_name or "GLOBAL", function_name)
        
        if module_name not in sys.modules:
            logger.error("Module %s not in sys.modules", module_name)
            return False
            
        module = sys.modules[module_name]
        file_path = getattr(module, "__file__", None)
        
        if not file_path:
            logger.error("No file path for module %s", module_name)
            return False
            
        # Parse existing AST
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
            
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error("Original source has syntax errors: %s", e)
            return False
            
        # Parse patch code
        try:
            patch_tree = ast.parse(patch_code.strip())
            if not patch_tree.body:
                raise ValueError("Patch code is empty")
            patch_node = patch_tree.body[0]
            if not isinstance(patch_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                raise ValueError("Patch code must be a function definition")
            if patch_node.name != function_name:
                raise ValueError(f"Patch function name '{patch_node.name}' does not match target '{function_name}'")
        except Exception as e:
            logger.error("Patch code is invalid: %s", e)
            return False
        
        # Apply transformation
        transformer = _HealingTransformer(function_name, class_name, patch_node)
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        
        if not transformer.patched:
            logger.error("Target %s.%s not found in AST of %s", class_name or "GLOBAL", function_name, file_path)
            return False
            
        new_source = ast.unparse(new_tree)
        
        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_source)
            
        # Sandbox Validation
        try:
            seal = SandboxValidator.validate_patch(file_path, test_path)
        except RuntimeError as e:
            logger.error("Sandbox validation rejected patch: %s", e)
            # Rollback
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(source)
            return False
            
        # Hot Swap
        try:
            success = HotSwapper.apply_patch(module_name, function_name, seal, class_name=class_name)
            return success
        except Exception as e:
            logger.error("Hot Swap failed: %s", e)
            # Rollback
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(source)
            return False
