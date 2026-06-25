import ast
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

class MutationOperator(ast.NodeTransformer):
    def __init__(self, target_line: int):
        self.target_line = target_line
        self.mutated = False

    def visit_Compare(self, node):
        if hasattr(node, 'lineno') and node.lineno == self.target_line and not self.mutated:
            # Simple mutation: invert == and !=
            if isinstance(node.ops[0], ast.Eq):
                node.ops[0] = ast.NotEq()
                self.mutated = True
            elif isinstance(node.ops[0], ast.NotEq):
                node.ops[0] = ast.Eq()
                self.mutated = True
            elif isinstance(node.ops[0], ast.Lt):
                node.ops[0] = ast.LtE()
                self.mutated = True
            elif isinstance(node.ops[0], ast.Gt):
                node.ops[0] = ast.GtE()
                self.mutated = True
        return self.generic_visit(node)

    def visit_Return(self, node):
        if hasattr(node, 'lineno') and node.lineno == self.target_line and not self.mutated:
            # Change return True to return False
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                node.value.value = not node.value.value
                self.mutated = True
        return self.generic_visit(node)

class MutationTester:
    """
    APEX-049: Tests Adversariales por Mutación.
    Ejecuta mutaciones estructurales en AST (inversión lógica, off-by-one).
    Si los tests pasan, el mutante sobrevive y la aserción original era débil.
    """

    def __init__(self, test_cmd: str = "pytest"):
        self.test_cmd = test_cmd

    def mutate_and_test(self, file_path: str, target_lines: list[int]) -> dict[str, Any]:
        with open(file_path, encoding="utf-8") as f:
            original_source = f.read()

        results = {
            "mutants_created": 0,
            "mutants_killed": 0,
            "mutants_survived": 0,
            "survivors": []
        }

        try:
            ast.parse(original_source)
        except SyntaxError:
            logger.error(f"Syntax error in {file_path}")
            return results

        for line in target_lines:
            mutator = MutationOperator(line)
            mutated_tree = mutator.visit(ast.parse(original_source))
            
            if not mutator.mutated:
                continue

            mutated_source = ast.unparse(mutated_tree)
            results["mutants_created"] += 1
            
            # Write mutant to disk
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(mutated_source)

            try:
                # Run tests
                proc = subprocess.run(
                    self.test_cmd.split(),
                    capture_output=True,
                    timeout=15
                )

                if proc.returncode == 0:
                    # Test passed! The mutant SURVIVED (bad)
                    results["mutants_survived"] += 1
                    results["survivors"].append(line)
                    logger.warning(f"Mutant SURVIVED at line {line} in {file_path}")
                else:
                    # Test failed! The mutant was KILLED (good)
                    results["mutants_killed"] += 1
                    logger.info(f"Mutant KILLED at line {line} in {file_path}")

            except subprocess.TimeoutExpired:
                # Timeout counts as killed (infinite loop)
                results["mutants_killed"] += 1
            finally:
                # Restore original file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(original_source)

        return results
